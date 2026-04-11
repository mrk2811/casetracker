"""
HTTP fallback engine using curl_cffi for court website scraping.

Provides a curl_cffi-based fallback when the primary httpx scraper
is blocked by Cloudflare or other TLS-fingerprint-based protections.
curl_cffi impersonates real browser TLS fingerprints, which bypasses
Cloudflare's managed challenge without needing a full headless browser.
"""

import asyncio
import logging
import random
import time
from typing import Optional

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from app.scraper.engine import ScrapeResult, USER_AGENTS

logger = logging.getLogger(__name__)


class BrowserEngine:
    """
    curl_cffi-based HTTP engine that impersonates real browser TLS fingerprints.

    Used as a fallback when the primary httpx-based ScraperEngine fails
    due to Cloudflare or similar TLS-fingerprint-based protections.

    Why curl_cffi instead of Selenium?
    Cloudflare's managed challenge specifically detects and blocks headless
    Chrome/Chromium browsers.  curl_cffi uses curl-impersonate under the
    hood, which reproduces the exact TLS handshake of a real Chrome browser,
    bypassing the fingerprint check without needing a full browser process.
    """

    def __init__(self) -> None:
        self._session: Optional[cffi_requests.Session] = None

    def _get_session(self) -> cffi_requests.Session:
        """Get or create the curl_cffi session with Chrome impersonation."""
        if self._session is None:
            self._session = cffi_requests.Session(impersonate="chrome")
        return self._session

    async def get(
        self, url: str, *, retries: int = 3
    ) -> ScrapeResult:
        """Perform a GET request, retrying on Cloudflare 403s.

        Cloudflare's managed challenge is inconsistent — the same URL may
        return 403 on one attempt and 200 on the next.  We retry up to
        *retries* times with a fresh session each attempt.
        """
        last_result: Optional[ScrapeResult] = None
        for attempt in range(1, retries + 1):
            start_time = time.monotonic()
            try:
                session = self._get_session()
                response = await asyncio.to_thread(
                    session.get,
                    url,
                    headers={"User-Agent": random.choice(USER_AGENTS)},
                    timeout=30,
                )
                elapsed_ms = (time.monotonic() - start_time) * 1000
                html = response.text

                if response.status_code == 200 and "just a moment" not in html[:500].lower():
                    soup = BeautifulSoup(html, "lxml")
                    return ScrapeResult(
                        success=True,
                        html=html,
                        soup=soup,
                        status_code=response.status_code,
                        response_time_ms=elapsed_ms,
                    )

                # Cloudflare blocked — reset session and retry
                logger.info(
                    "Browser GET attempt %d/%d blocked (HTTP %d) for %s",
                    attempt, retries, response.status_code, url,
                )
                last_result = ScrapeResult(
                    success=False,
                    html=html,
                    status_code=response.status_code,
                    error_message=f"HTTP {response.status_code}",
                    response_time_ms=elapsed_ms,
                )
                # Reset session to get fresh TLS fingerprint / cookies
                self.close()
                await asyncio.sleep(random.uniform(0.5, 1.5))

            except Exception as exc:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                logger.error("Browser GET attempt %d failed for %s: %s", attempt, url, exc)
                last_result = ScrapeResult(
                    success=False,
                    error_message=f"Browser fallback error: {exc}",
                    response_time_ms=elapsed_ms,
                )
                self.close()
                await asyncio.sleep(random.uniform(0.5, 1.5))

        return last_result or ScrapeResult(
            success=False,
            error_message="All browser GET retries exhausted",
        )

    async def post_form(
        self,
        url: str,
        data: dict[str, str],
    ) -> ScrapeResult:
        """
        Submit a form via POST using the impersonating session.

        Args:
            url: URL to POST the form data to.
            data: Form fields as key-value pairs.
        """
        start_time = time.monotonic()
        try:
            session = self._get_session()

            # Small random delay to mimic human timing
            await asyncio.sleep(random.uniform(0.5, 1.5))

            response = await asyncio.to_thread(
                session.post,
                url,
                data=data,
                headers={"User-Agent": random.choice(USER_AGENTS)},
                timeout=30,
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000
            html = response.text

            if response.status_code != 200:
                return ScrapeResult(
                    success=False,
                    html=html,
                    status_code=response.status_code,
                    error_message=f"HTTP {response.status_code}",
                    response_time_ms=elapsed_ms,
                )

            soup = BeautifulSoup(html, "lxml")
            return ScrapeResult(
                success=True,
                html=html,
                soup=soup,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error("Browser POST form failed for %s: %s", url, exc)
            return ScrapeResult(
                success=False,
                error_message=f"Browser fallback error: {exc}",
                response_time_ms=elapsed_ms,
            )

    def close(self) -> None:
        """Close the session and release resources."""
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None

    def __del__(self) -> None:
        self.close()
