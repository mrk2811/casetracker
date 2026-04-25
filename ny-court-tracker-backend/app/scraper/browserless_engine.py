"""
Browserless.io integration engine for court website scraping.

Uses a two-step approach to handle hCaptcha-protected sites:

1. **Unblock API** -- POST to ``/unblock`` which bypasses Cloudflare and
   hCaptcha automatically, then returns a ``browserWSEndpoint`` for the
   *already-unblocked* browser session.
2. **Playwright CDP** -- connect to the returned endpoint, fill the search
   form, submit, and extract results.

This avoids the 60-second WebSocket session limit on the free tier by
letting the /unblock API handle the slow captcha-solving step, and only
using the WebSocket session for the fast form-fill + submit step.

Fallback: if /unblock doesn't return a browserWSEndpoint, the engine
falls back to a direct CDP connection with solveCaptchas=true.
"""

import logging
import os
import time
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser

from app.scraper.engine import ScrapeResult

logger = logging.getLogger(__name__)

# Browserless connection settings
BROWSERLESS_DEFAULT_REGION = "production-sfo.browserless.io"
# TTL for the browser session after /unblock returns (ms)
BROWSERLESS_SESSION_TTL_MS = 30_000


def _get_browserless_token() -> Optional[str]:
    """Return the Browserless API token from environment."""
    return os.environ.get("BROWSERLESS_API_TOKEN")


def _get_browserless_base_url() -> str:
    """Return the Browserless HTTPS base URL for REST API calls."""
    region = os.environ.get("BROWSERLESS_REGION", BROWSERLESS_DEFAULT_REGION)
    return f"https://{region}"


class BrowserlessEngine:
    """
    Browserless.io-powered browser engine for scraping hCaptcha-protected sites.

    Uses the /unblock REST API to bypass Cloudflare + hCaptcha, then
    connects Playwright to the unblocked browser session to fill forms
    and extract results.

    Each search session:
    1. POST /unblock to get past Cloudflare/hCaptcha (returns browserWSEndpoint)
    2. Connect Playwright to the live browser session
    3. Fill and submit the search form
    4. Extract the results page HTML
    5. Close the connection

    Cost: ~10 units per /unblock call on Browserless free tier (1,000 units/month).
    """

    async def _call_unblock(
        self,
        url: str,
        *,
        want_endpoint: bool = True,
    ) -> dict[str, Any]:
        """Call the Browserless /unblock API.

        Args:
            url: The URL to unblock.
            want_endpoint: If True, request a browserWSEndpoint for further
                automation. If False, just return the page content.

        Returns:
            The JSON response dict with keys: content, cookies,
            screenshot, browserWSEndpoint.

        Raises:
            RuntimeError: If the API call fails.
        """
        token = _get_browserless_token()
        if not token:
            raise RuntimeError(
                "BROWSERLESS_API_TOKEN not set. "
                "Set the environment variable to enable automated searches."
            )

        base_url = _get_browserless_base_url()
        api_url = f"{base_url}/unblock?token={token}"

        payload: dict[str, Any] = {
            "url": url,
            "browserWSEndpoint": want_endpoint,
            "cookies": True,
            "content": True,
            "screenshot": False,
        }
        if want_endpoint:
            payload["ttl"] = BROWSERLESS_SESSION_TTL_MS

        logger.info("Calling /unblock for %s", url)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Browserless /unblock returned HTTP {resp.status_code}: "
                f"{resp.text[:500]}"
            )

        data: dict[str, Any] = resp.json()
        logger.info(
            "/unblock response: has_content=%s, has_endpoint=%s, cookies=%d",
            bool(data.get("content")),
            bool(data.get("browserWSEndpoint")),
            len(data.get("cookies") or []),
        )
        return data

    # ------------------------------------------------------------------
    # Local Civil Court search
    # ------------------------------------------------------------------

    async def search_local_by_index(
        self,
        case_type: str,
        number: str,
        year: str,
        court: str,
    ) -> ScrapeResult:
        """Search WebCivil Local by index number using Browserless.

        Args:
            case_type: Case type code (e.g. "LT", "CV", "SC")
            number: Index number (e.g. "332489")
            year: Two-digit year (e.g. "24")
            court: Court code (e.g. "BX" for Bronx)

        Returns:
            ScrapeResult with the search results page HTML/soup.
        """
        token = _get_browserless_token()
        if not token:
            return ScrapeResult(
                success=False,
                error_message=(
                    "BROWSERLESS_API_TOKEN not set. "
                    "Set the environment variable to enable automated searches."
                ),
            )

        start_time = time.monotonic()
        search_url = (
            "https://iapps.courts.state.ny.us/webcivilLocal/LCSearch?param=I"
        )

        try:
            # Step 1: Unblock the search page (solve captcha if needed)
            data = await self._call_unblock(search_url, want_endpoint=True)
            ws_endpoint = data.get("browserWSEndpoint")

            if not ws_endpoint:
                # No live session returned -- fall back to direct CDP
                logger.warning(
                    "No browserWSEndpoint returned, falling back to direct CDP"
                )
                return await self._direct_cdp_search_local(
                    case_type, number, year, court, start_time
                )

            # Step 2: Connect to the unblocked browser and fill the form
            browser: Optional[Browser] = None
            try:
                async with async_playwright() as pw:
                    logger.info(
                        "Connecting to unblocked browser for Local search: "
                        "%s-%s-%s/%s",
                        case_type, number, year, court,
                    )
                    browser = await pw.chromium.connect_over_cdp(ws_endpoint)
                    context = browser.contexts[0]
                    page = (
                        context.pages[0]
                        if context.pages
                        else await context.new_page()
                    )

                    # The page should already be on the search form
                    current_url = page.url
                    logger.info("Browser is on: %s", current_url)

                    # Make sure we're on the right page with the form
                    page_content = await page.content()
                    if "txtIndexNumber" not in page_content:
                        logger.info("Navigating to search form...")
                        await page.goto(
                            search_url,
                            wait_until="domcontentloaded",
                            timeout=15000,
                        )

                    # Fill the search form
                    await page.select_option(
                        'select[name="cboCaseType"]', case_type
                    )
                    await page.fill('input[name="txtIndexNumber"]', number)
                    await page.fill('input[name="txtIndexYear"]', year)
                    await page.select_option(
                        'select[name="cboIndexCourtIndicator"]', court
                    )

                    logger.info("Submitting Local search form")

                    # Click Find Case(s) and wait for navigation
                    async with page.expect_navigation(
                        wait_until="domcontentloaded", timeout=20000
                    ):
                        await page.click('input[name="btnFindCase"]')

                    result_content = await page.content()
                    elapsed_ms = (time.monotonic() - start_time) * 1000

                    return self._build_result(
                        result_content, elapsed_ms, "Local",
                        result_marker="LCCaseInfo",
                    )
            finally:
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "Browserless Local search failed: %s (elapsed %.0fms)",
                exc, elapsed_ms,
            )
            return ScrapeResult(
                success=False,
                error_message=f"Browserless error: {exc}",
                response_time_ms=elapsed_ms,
            )

    # ------------------------------------------------------------------
    # Supreme Court search
    # ------------------------------------------------------------------

    async def search_supreme_by_index(
        self,
        index_number: str,
        county_court_value: Optional[str] = None,
    ) -> ScrapeResult:
        """Search WebCivil Supreme by index number using Browserless.

        Args:
            index_number: Supreme Court index number (e.g. "152847/2026")
            county_court_value: Optional court select value for county filter

        Returns:
            ScrapeResult with the search results page HTML/soup.
        """
        token = _get_browserless_token()
        if not token:
            return ScrapeResult(
                success=False,
                error_message=(
                    "BROWSERLESS_API_TOKEN not set. "
                    "Set the environment variable to enable automated searches."
                ),
            )

        start_time = time.monotonic()
        search_url = (
            "https://iapps.courts.state.ny.us/webcivil/FCASSearch?param=I"
        )

        try:
            # Step 1: Unblock the search page
            data = await self._call_unblock(search_url, want_endpoint=True)
            ws_endpoint = data.get("browserWSEndpoint")

            if not ws_endpoint:
                logger.warning(
                    "No browserWSEndpoint returned for Supreme search"
                )
                return await self._direct_cdp_search_supreme(
                    index_number, county_court_value, start_time
                )

            # Step 2: Connect and fill the form
            browser: Optional[Browser] = None
            try:
                async with async_playwright() as pw:
                    logger.info(
                        "Connecting to unblocked browser for Supreme "
                        "search: %s", index_number,
                    )
                    browser = await pw.chromium.connect_over_cdp(ws_endpoint)
                    context = browser.contexts[0]
                    page = (
                        context.pages[0]
                        if context.pages
                        else await context.new_page()
                    )

                    page_content = await page.content()
                    if "txtIndex" not in page_content:
                        logger.info("Navigating to Supreme search form...")
                        await page.goto(
                            search_url,
                            wait_until="domcontentloaded",
                            timeout=15000,
                        )

                    # Fill the index number
                    await page.fill('input[name="txtIndex"]', index_number)

                    # Set county if provided
                    if county_court_value:
                        await page.select_option(
                            'select[name="cboCourt"]', county_court_value
                        )

                    logger.info("Submitting Supreme search form")
                    async with page.expect_navigation(
                        wait_until="domcontentloaded", timeout=20000
                    ):
                        await page.click('input[name="btnFindCase"]')

                    result_content = await page.content()
                    elapsed_ms = (time.monotonic() - start_time) * 1000

                    return self._build_result(
                        result_content, elapsed_ms, "Supreme",
                        result_marker="FCASCaseDetail",
                    )
            finally:
                if browser:
                    try:
                        await browser.close()
                    except Exception:
                        pass

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "Browserless Supreme search failed: %s (elapsed %.0fms)",
                exc, elapsed_ms,
            )
            return ScrapeResult(
                success=False,
                error_message=f"Browserless error: {exc}",
                response_time_ms=elapsed_ms,
            )

    # ------------------------------------------------------------------
    # Detail page fetching
    # ------------------------------------------------------------------

    async def get_page_content(self, url: str) -> ScrapeResult:
        """Fetch any WebCivil page using Browserless (for detail pages).

        Uses /unblock in content-only mode (no live browser session needed
        since we just need to read the page).

        Args:
            url: Full URL to navigate to.

        Returns:
            ScrapeResult with the page HTML/soup.
        """
        token = _get_browserless_token()
        if not token:
            return ScrapeResult(
                success=False,
                error_message="BROWSERLESS_API_TOKEN not set.",
            )

        start_time = time.monotonic()

        try:
            data = await self._call_unblock(url, want_endpoint=False)
            content = data.get("content") or ""
            elapsed_ms = (time.monotonic() - start_time) * 1000
            soup = BeautifulSoup(content, "lxml")

            return ScrapeResult(
                success=True,
                html=content,
                soup=soup,
                status_code=200,
                response_time_ms=elapsed_ms,
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error("Browserless page fetch failed: %s", exc)
            return ScrapeResult(
                success=False,
                error_message=f"Browserless error: {exc}",
                response_time_ms=elapsed_ms,
            )

    # ------------------------------------------------------------------
    # Result builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_result(
        html: str,
        elapsed_ms: float,
        label: str,
        *,
        result_marker: str,
    ) -> ScrapeResult:
        """Build a ScrapeResult from raw HTML content."""
        soup = BeautifulSoup(html, "lxml")

        has_results = result_marker in html
        has_no_cases = "No Cases Found" in html
        has_captcha = (
            "I am human" in html
            or "captcha_form" in html.lower()
        )

        if has_captcha:
            logger.warning(
                "Captcha still present after /unblock for %s search "
                "(elapsed %.0fms)", label, elapsed_ms,
            )
            return ScrapeResult(
                success=False,
                html=html,
                soup=soup,
                status_code=200,
                error_message="Captcha not solved by Browserless",
                captcha_detected=True,
                response_time_ms=elapsed_ms,
            )

        logger.info(
            "%s search completed: has_results=%s, no_cases=%s "
            "(elapsed %.0fms)",
            label, has_results, has_no_cases, elapsed_ms,
        )
        return ScrapeResult(
            success=True,
            html=html,
            soup=soup,
            status_code=200,
            response_time_ms=elapsed_ms,
        )

    # ------------------------------------------------------------------
    # Direct CDP fallback (when /unblock doesn't return endpoint)
    # ------------------------------------------------------------------

    async def _direct_cdp_search_local(
        self,
        case_type: str,
        number: str,
        year: str,
        court: str,
        start_time: float,
    ) -> ScrapeResult:
        """Direct CDP connection fallback for Local search.

        Used when /unblock doesn't return a browserWSEndpoint.
        Connects directly to Browserless stealth mode with solveCaptchas.
        """
        token = _get_browserless_token()
        if not token:
            return ScrapeResult(
                success=False,
                error_message="BROWSERLESS_API_TOKEN not set.",
            )

        region = os.environ.get(
            "BROWSERLESS_REGION", BROWSERLESS_DEFAULT_REGION
        )
        ws_url = (
            f"wss://{region}/stealth?token={token}"
            f"&solveCaptchas=true&timeout=55000"
        )

        browser: Optional[Browser] = None
        try:
            async with async_playwright() as pw:
                logger.info("Direct CDP fallback for Local search")
                browser = await pw.chromium.connect_over_cdp(ws_url)
                context = browser.contexts[0]
                page = (
                    context.pages[0]
                    if context.pages
                    else await context.new_page()
                )

                search_url = (
                    "https://iapps.courts.state.ny.us"
                    "/webcivilLocal/LCSearch?param=I"
                )
                await page.goto(
                    search_url, wait_until="domcontentloaded", timeout=25000
                )

                # Wait for the form to be available
                await page.wait_for_selector(
                    'input[name="txtIndexNumber"]', timeout=25000
                )

                await page.select_option(
                    'select[name="cboCaseType"]', case_type
                )
                await page.fill('input[name="txtIndexNumber"]', number)
                await page.fill('input[name="txtIndexYear"]', year)
                await page.select_option(
                    'select[name="cboIndexCourtIndicator"]', court
                )

                async with page.expect_navigation(
                    wait_until="domcontentloaded", timeout=20000
                ):
                    await page.click('input[name="btnFindCase"]')

                result_content = await page.content()
                elapsed_ms = (time.monotonic() - start_time) * 1000

                return self._build_result(
                    result_content, elapsed_ms, "Local (CDP)",
                    result_marker="LCCaseInfo",
                )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error("Direct CDP Local search failed: %s", exc)
            return ScrapeResult(
                success=False,
                error_message=f"Browserless CDP error: {exc}",
                response_time_ms=elapsed_ms,
            )
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

    async def _direct_cdp_search_supreme(
        self,
        index_number: str,
        county_court_value: Optional[str],
        start_time: float,
    ) -> ScrapeResult:
        """Direct CDP connection fallback for Supreme search."""
        token = _get_browserless_token()
        if not token:
            return ScrapeResult(
                success=False,
                error_message="BROWSERLESS_API_TOKEN not set.",
            )

        region = os.environ.get(
            "BROWSERLESS_REGION", BROWSERLESS_DEFAULT_REGION
        )
        ws_url = (
            f"wss://{region}/stealth?token={token}"
            f"&solveCaptchas=true&timeout=55000"
        )

        browser: Optional[Browser] = None
        try:
            async with async_playwright() as pw:
                logger.info("Direct CDP fallback for Supreme search")
                browser = await pw.chromium.connect_over_cdp(ws_url)
                context = browser.contexts[0]
                page = (
                    context.pages[0]
                    if context.pages
                    else await context.new_page()
                )

                search_url = (
                    "https://iapps.courts.state.ny.us"
                    "/webcivil/FCASSearch?param=I"
                )
                await page.goto(
                    search_url, wait_until="domcontentloaded", timeout=25000
                )

                await page.wait_for_selector(
                    'input[name="txtIndex"]', timeout=25000
                )

                await page.fill('input[name="txtIndex"]', index_number)
                if county_court_value:
                    await page.select_option(
                        'select[name="cboCourt"]', county_court_value
                    )

                async with page.expect_navigation(
                    wait_until="domcontentloaded", timeout=20000
                ):
                    await page.click('input[name="btnFindCase"]')

                result_content = await page.content()
                elapsed_ms = (time.monotonic() - start_time) * 1000

                return self._build_result(
                    result_content, elapsed_ms, "Supreme (CDP)",
                    result_marker="FCASCaseDetail",
                )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error("Direct CDP Supreme search failed: %s", exc)
            return ScrapeResult(
                success=False,
                error_message=f"Browserless CDP error: {exc}",
                response_time_ms=elapsed_ms,
            )
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
