"""
Captcha solver engine for court website scraping.

Uses third-party CAPTCHA solving services (2Captcha, CapSolver) to obtain
valid hCaptcha tokens, then submits them alongside form data using curl_cffi
for browser-grade TLS fingerprinting.

Architecture:
1. curl_cffi GET — load the search form page (establishes session cookies).
2. Captcha solver API — request an hCaptcha token for the target URL/sitekey.
3. curl_cffi POST — submit the form with the solved token + form data.

This avoids needing a full headless browser (Playwright/Selenium) and works
from any IP since the captcha solver service uses its own residential IPs.

Environment variables:
    CAPTCHA_SOLVER_API_KEY  — API key for the captcha solving service.
    CAPTCHA_SOLVER_SERVICE  — Service name: "2captcha" (default) or "capsolver".
"""

import asyncio
import logging
import os
import time
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.scraper.engine import ScrapeResult

logger = logging.getLogger(__name__)

# Known hCaptcha sitekey used by WebCivil Local/Supreme submit buttons
DEFAULT_HCAPTCHA_SITEKEY = "6c824b97-caeb-4a2a-9144-db4f1c9f86d0"

# 2Captcha API endpoints
_2CAPTCHA_SUBMIT_URL = "https://2captcha.com/in.php"
_2CAPTCHA_RESULT_URL = "https://2captcha.com/res.php"

# CapSolver API endpoint
_CAPSOLVER_API_URL = "https://api.capsolver.com"

# Polling configuration
_POLL_INTERVAL_SEC = 5
_MAX_POLL_ATTEMPTS = 60  # 5 minutes max wait


def _get_captcha_api_key() -> Optional[str]:
    """Return the captcha solver API key from environment."""
    return os.environ.get("CAPTCHA_SOLVER_API_KEY")


def _get_captcha_service() -> str:
    """Return the captcha solver service name."""
    return os.environ.get("CAPTCHA_SOLVER_SERVICE", "2captcha")


class CaptchaSolver:
    """
    Captcha solver that uses third-party services to solve hCaptcha challenges.

    Supports:
    - 2Captcha (default) — human solvers, ~$2.99/1000 solves
    - CapSolver — AI + human hybrid, similar pricing

    The solver obtains a valid hCaptcha response token that can be included
    in form POST data to bypass the captcha gate.
    """

    async def solve_hcaptcha(
        self,
        sitekey: str,
        page_url: str,
        *,
        invisible: bool = True,
    ) -> str:
        """Solve an hCaptcha challenge and return the response token.

        Args:
            sitekey: The hCaptcha data-sitekey value from the page.
            page_url: The full URL of the page containing the captcha.
            invisible: Whether the hCaptcha is in invisible mode.

        Returns:
            The hCaptcha response token string.

        Raises:
            RuntimeError: If the API key is missing or solving fails.
        """
        api_key = _get_captcha_api_key()
        if not api_key:
            raise RuntimeError(
                "CAPTCHA_SOLVER_API_KEY not set. "
                "Set the environment variable to enable automated CAPTCHA solving."
            )

        service = _get_captcha_service()
        logger.info(
            "Solving hCaptcha via %s (sitekey=%s, url=%s, invisible=%s)",
            service, sitekey[:12] + "...", page_url, invisible,
        )

        start = time.monotonic()

        if service == "capsolver":
            token = await self._solve_with_capsolver(
                api_key, sitekey, page_url, invisible=invisible
            )
        else:
            token = await self._solve_with_2captcha(
                api_key, sitekey, page_url, invisible=invisible
            )

        elapsed = time.monotonic() - start
        logger.info(
            "hCaptcha solved in %.1fs (token length: %d)", elapsed, len(token)
        )
        return token

    # ------------------------------------------------------------------
    # 2Captcha implementation
    # ------------------------------------------------------------------

    async def _solve_with_2captcha(
        self,
        api_key: str,
        sitekey: str,
        page_url: str,
        *,
        invisible: bool = True,
    ) -> str:
        """Submit and poll 2Captcha for an hCaptcha solution."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Submit the captcha task
            submit_params = {
                "key": api_key,
                "method": "hcaptcha",
                "sitekey": sitekey,
                "pageurl": page_url,
                "json": "1",
            }
            if invisible:
                submit_params["invisible"] = "1"

            resp = await client.post(_2CAPTCHA_SUBMIT_URL, data=submit_params)
            result = resp.json()

            if result.get("status") != 1:
                error = result.get("request", "Unknown error")
                raise RuntimeError(f"2Captcha submit failed: {error}")

            task_id = result["request"]
            logger.info("2Captcha task submitted: %s", task_id)

            # Step 2: Poll for the result
            for attempt in range(1, _MAX_POLL_ATTEMPTS + 1):
                await asyncio.sleep(_POLL_INTERVAL_SEC)

                poll_resp = await client.get(
                    _2CAPTCHA_RESULT_URL,
                    params={
                        "key": api_key,
                        "action": "get",
                        "id": task_id,
                        "json": "1",
                    },
                )
                poll_result = poll_resp.json()
                status = poll_result.get("status", -1)
                request_val = poll_result.get("request", "")

                if status == 1:
                    logger.info(
                        "2Captcha solved on poll %d (token: %s...)",
                        attempt, request_val[:40],
                    )
                    return request_val

                if request_val == "ERROR_CAPTCHA_UNSOLVABLE":
                    raise RuntimeError("2Captcha: captcha marked unsolvable")

                if request_val != "CAPCHA_NOT_READY":
                    logger.warning(
                        "2Captcha poll %d: unexpected response: %s",
                        attempt, request_val,
                    )

            raise RuntimeError(
                f"2Captcha: timed out after {_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_SEC}s"
            )

    # ------------------------------------------------------------------
    # CapSolver implementation
    # ------------------------------------------------------------------

    async def _solve_with_capsolver(
        self,
        api_key: str,
        sitekey: str,
        page_url: str,
        *,
        invisible: bool = True,
    ) -> str:
        """Submit and poll CapSolver for an hCaptcha solution."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Create task
            task_payload = {
                "type": "HCaptchaTaskProxyLess",
                "websiteURL": page_url,
                "websiteKey": sitekey,
            }
            if invisible:
                task_payload["isInvisible"] = True

            resp = await client.post(
                f"{_CAPSOLVER_API_URL}/createTask",
                json={"clientKey": api_key, "task": task_payload},
            )
            result = resp.json()

            if result.get("errorId", 0) != 0:
                error = result.get("errorDescription", "Unknown error")
                raise RuntimeError(f"CapSolver submit failed: {error}")

            task_id = result["taskId"]
            logger.info("CapSolver task submitted: %s", task_id)

            # Step 2: Poll for result
            for attempt in range(1, _MAX_POLL_ATTEMPTS + 1):
                await asyncio.sleep(_POLL_INTERVAL_SEC)

                poll_resp = await client.post(
                    f"{_CAPSOLVER_API_URL}/getTaskResult",
                    json={"clientKey": api_key, "taskId": task_id},
                )
                poll_result = poll_resp.json()

                if poll_result.get("errorId", 0) != 0:
                    error = poll_result.get("errorDescription", "Unknown")
                    raise RuntimeError(f"CapSolver error: {error}")

                status = poll_result.get("status", "")
                if status == "ready":
                    solution = poll_result.get("solution", {})
                    token = solution.get("gRecaptchaResponse", "")
                    if not token:
                        raise RuntimeError("CapSolver: empty token in solution")
                    logger.info(
                        "CapSolver solved on poll %d (token: %s...)",
                        attempt, token[:40],
                    )
                    return token

            raise RuntimeError(
                f"CapSolver: timed out after {_MAX_POLL_ATTEMPTS * _POLL_INTERVAL_SEC}s"
            )


class CaptchaSolverEngine:
    """
    High-level engine that combines captcha solving with form submission.

    Uses CaptchaSolver to obtain tokens and curl_cffi to submit forms,
    providing the same interface as BrowserlessEngine for drop-in replacement.
    """

    def __init__(self) -> None:
        self._solver = CaptchaSolver()

    async def search_local_by_index(
        self,
        case_type: str,
        number: str,
        year: str,
        court: str,
    ) -> ScrapeResult:
        """Search WebCivil Local by index number with automatic CAPTCHA solving.

        Args:
            case_type: Case type code (e.g. "LT", "CV", "SC")
            number: Index number (e.g. "332489")
            year: Two-digit year (e.g. "24")
            court: Court code (e.g. "BX" for Bronx)

        Returns:
            ScrapeResult with the search results page HTML/soup.
        """
        search_url = (
            "https://iapps.courts.state.ny.us/webcivilLocal/LCSearch"
        )
        form_url = f"{search_url}?param=I"

        start_time = time.monotonic()

        try:
            # Step 1: Solve hCaptcha
            token = await self._solver.solve_hcaptcha(
                sitekey=DEFAULT_HCAPTCHA_SITEKEY,
                page_url=form_url,
            )

            # Step 2: Submit form with token using curl_cffi
            from curl_cffi.requests import AsyncSession

            async with AsyncSession(impersonate="chrome") as session:
                # GET the form page first to establish session cookies
                get_resp = await session.get(form_url)
                logger.info(
                    "Local search form GET: HTTP %d", get_resp.status_code
                )

                # POST with form data + captcha token
                form_data = {
                    "hWhichPage": "I",
                    "hCourtType": "Local",
                    "hPageNumber": "1",
                    "hSearchKey": "",
                    "cboCaseType": case_type,
                    "txtIndexNumber": number,
                    "txtIndexYear": year,
                    "cboIndexCourtIndicator": court,
                    "cboSort": "court",
                    "rbOutputFormat": "HTML",
                    "btnFindCase": "Find Case(s)",
                    "h-captcha-response": token,
                    "g-recaptcha-response": token,
                }

                post_resp = await session.post(
                    search_url,
                    data=form_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": form_url,
                        "Origin": "https://iapps.courts.state.ny.us",
                    },
                )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            html = post_resp.text

            return self._build_result(
                html, elapsed_ms, "Local",
                result_marker="LCCaseInfo",
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "Captcha solver Local search failed: %s (elapsed %.0fms)",
                exc, elapsed_ms,
            )
            return ScrapeResult(
                success=False,
                error_message=f"Captcha solver error: {exc}",
                response_time_ms=elapsed_ms,
            )

    async def search_supreme_by_index(
        self,
        index_number: str,
        county_court_value: Optional[str] = None,
    ) -> ScrapeResult:
        """Search WebCivil Supreme by index number with automatic CAPTCHA solving.

        Args:
            index_number: Supreme Court index number (e.g. "152847/2026")
            county_court_value: Optional court select value for county filter

        Returns:
            ScrapeResult with the search results page HTML/soup.
        """
        search_url = (
            "https://iapps.courts.state.ny.us/webcivil/FCASSearch"
        )
        form_url = f"{search_url}?param=I"

        start_time = time.monotonic()

        try:
            # Step 1: Solve hCaptcha
            token = await self._solver.solve_hcaptcha(
                sitekey=DEFAULT_HCAPTCHA_SITEKEY,
                page_url=form_url,
            )

            # Step 2: Submit form with token using curl_cffi
            from curl_cffi.requests import AsyncSession

            async with AsyncSession(impersonate="chrome") as session:
                get_resp = await session.get(form_url)
                logger.info(
                    "Supreme search form GET: HTTP %d", get_resp.status_code
                )

                form_data = {
                    "hWhichPage": "I",
                    "hCourtType": "Supreme",
                    "hPageNumber": "1",
                    "hSearchKey": "",
                    "txtIndex": index_number,
                    "rbStatus": "open",
                    "rbFutureCases": "N",
                    "rbOutputFormat": "HTML",
                    "cboSort": "index_number",
                    "cboYearOfFiling": "0",
                    "btnFindCase": "Find Case(s)",
                    "h-captcha-response": token,
                    "g-recaptcha-response": token,
                }
                if county_court_value:
                    form_data["cboCourt"] = county_court_value

                post_resp = await session.post(
                    search_url,
                    data=form_data,
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": form_url,
                        "Origin": "https://iapps.courts.state.ny.us",
                    },
                )

            elapsed_ms = (time.monotonic() - start_time) * 1000
            html = post_resp.text

            return self._build_result(
                html, elapsed_ms, "Supreme",
                result_marker="FCASCaseDetail",
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error(
                "Captcha solver Supreme search failed: %s (elapsed %.0fms)",
                exc, elapsed_ms,
            )
            return ScrapeResult(
                success=False,
                error_message=f"Captcha solver error: {exc}",
                response_time_ms=elapsed_ms,
            )

    async def get_page_content(self, url: str) -> ScrapeResult:
        """Fetch any WebCivil page using curl_cffi (for detail pages).

        Detail pages may still require a valid session, so we solve the
        captcha gate first if needed.

        Args:
            url: Full URL to navigate to.

        Returns:
            ScrapeResult with the page HTML/soup.
        """
        start_time = time.monotonic()

        try:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession(impersonate="chrome") as session:
                resp = await session.get(url)
                html = resp.text

                # Check if we hit a captcha gate
                if "I am human" in html or "h-captcha" in html.lower():
                    logger.info(
                        "Detail page hit captcha gate, solving..."
                    )
                    # Solve captcha and retry with the established session
                    token = await self._solver.solve_hcaptcha(
                        sitekey=DEFAULT_HCAPTCHA_SITEKEY,
                        page_url=url,
                    )
                    # POST the captcha solution to get past the gate
                    gate_resp = await session.post(
                        url,
                        data={
                            "h-captcha-response": token,
                            "g-recaptcha-response": token,
                        },
                        headers={
                            "Content-Type": "application/x-www-form-urlencoded",
                            "Referer": url,
                        },
                    )
                    # Now retry the original page
                    resp = await session.get(url)
                    html = resp.text

            elapsed_ms = (time.monotonic() - start_time) * 1000
            soup = BeautifulSoup(html, "lxml")

            return ScrapeResult(
                success=True,
                html=html,
                soup=soup,
                status_code=200,
                response_time_ms=elapsed_ms,
            )

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error("Captcha solver page fetch failed: %s", exc)
            return ScrapeResult(
                success=False,
                error_message=f"Captcha solver error: {exc}",
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
                "Captcha still present after token submission for %s search "
                "(elapsed %.0fms)", label, elapsed_ms,
            )
            return ScrapeResult(
                success=False,
                html=html,
                soup=soup,
                status_code=200,
                error_message="Captcha token rejected by server",
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
