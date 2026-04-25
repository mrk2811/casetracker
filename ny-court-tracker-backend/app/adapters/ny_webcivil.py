"""
NY WebCivil adapter — scrapes iapps.courts.state.ny.us court systems.

Supports two court systems on the same domain:
- WebCivil Supreme  (/webcivil/FCASSearch) — Supreme & County Court cases.
- WebCivil Local    (/webcivilLocal/LCSearch) — Local Civil Courts including
  Housing Court / Landlord-Tenant, City Courts, District Courts.

The adapter auto-detects which system to query based on the index number format.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from app.adapters.base import (
    CaptchaRequiredError,
    CourtAdapter,
    CourtRecord,
    AppearanceRecord,
    SearchParams,
    CaseSource,
    CourtSystem,
)
from app.scraper.engine import ScraperEngine
from app.scraper.browser_engine import BrowserEngine
from app.scraper.browserless_engine import BrowserlessEngine
from app.scraper.captcha_solver import CaptchaSolverEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base URLs for the two court systems
# ---------------------------------------------------------------------------
BASE_URL_SUPREME = "https://iapps.courts.state.ny.us/webcivil"
BASE_URL_LOCAL = "https://iapps.courts.state.ny.us/webcivilLocal"

# Keep the old name as an alias so existing code that imports it still works.
BASE_URL = BASE_URL_SUPREME

# Search-form URLs (used by the browser fallback to establish sessions)
SUPREME_INDEX_SEARCH_URL = f"{BASE_URL_SUPREME}/FCASSearch?param=I"
SUPREME_PARTY_SEARCH_URL = f"{BASE_URL_SUPREME}/FCASSearch?param=P"
LOCAL_INDEX_SEARCH_URL = f"{BASE_URL_LOCAL}/LCSearch?param=I"
LOCAL_PARTY_SEARCH_URL = f"{BASE_URL_LOCAL}/LCSearch?param=P"

# Regex that matches a Local Civil Court index number.
# Format: <CaseType>-<Number>-<Year>/<CourtCode>
# e.g. LT-332489-24/BX, CV-000044-06/AU, SC-1234-23/NY
_LOCAL_INDEX_RE = re.compile(
    r"^(?P<case_type>[A-Z]{2})-(?P<number>\d+)-(?P<year>\d{2})/(?P<court>[A-Z]{2})$"
)

# Valid Local Civil case-type prefixes
_LOCAL_CASE_TYPES = {"CC", "CV", "LT", "MI", "NC", "RE", "SC", "TS"}

# Mapping of county names to court select values used by WebCivil
COUNTY_COURT_VALUES: dict[str, dict[str, str]] = {
    "albany": {"county": "1", "supreme": "2"},
    "allegany": {"county": "3", "supreme": "4"},
    "bronx": {"supreme": "124"},
    "broome": {"county": "5", "supreme": "6"},
    "cattaraugus": {"county": "7", "supreme": "8"},
    "cayuga": {"county": "9", "supreme": "10"},
    "chautauqua": {"county": "11", "supreme": "12"},
    "chemung": {"county": "13", "supreme": "14"},
    "chenango": {"county": "15", "supreme": "16"},
    "clinton": {"county": "17", "supreme": "18"},
    "columbia": {"county": "19", "supreme": "20"},
    "cortland": {"county": "21", "supreme": "22"},
    "delaware": {"county": "23", "supreme": "24"},
    "dutchess": {"county": "25", "supreme": "26"},
    "erie": {"county": "27", "supreme": "28"},
    "essex": {"county": "29", "supreme": "30"},
    "franklin": {"county": "31", "supreme": "32"},
    "fulton": {"county": "33", "supreme": "34"},
    "genesee": {"county": "35", "supreme": "36"},
    "greene": {"county": "37", "supreme": "38"},
    "hamilton": {"county": "39", "supreme": "40"},
    "herkimer": {"county": "41", "supreme": "42"},
    "jefferson": {"county": "43", "supreme": "44"},
    "kings": {"supreme": "46"},
    "lewis": {"county": "47", "supreme": "48"},
    "livingston": {"county": "49", "supreme": "50"},
    "madison": {"county": "51", "supreme": "52"},
    "monroe": {"county": "53", "supreme": "54"},
    "montgomery": {"county": "55", "supreme": "56"},
    "nassau": {"county": "57", "supreme": "58"},
    "new york": {"supreme": "60"},
    "niagara": {"county": "61", "supreme": "62"},
    "oneida": {"county": "63", "supreme": "64"},
    "onondaga": {"county": "65", "supreme": "66"},
    "ontario": {"county": "67", "supreme": "68"},
    "orange": {"county": "69", "supreme": "70"},
    "orleans": {"county": "71", "supreme": "72"},
    "oswego": {"county": "73", "supreme": "74"},
    "otsego": {"county": "75", "supreme": "76"},
    "putnam": {"county": "77", "supreme": "78"},
    "queens": {"supreme": "80"},
    "rensselaer": {"county": "81", "supreme": "82"},
    "richmond": {"supreme": "84"},
    "rockland": {"county": "85", "supreme": "86"},
    "saratoga": {"county": "89", "supreme": "90"},
    "schenectady": {"county": "91", "supreme": "92"},
    "schoharie": {"county": "93", "supreme": "94"},
    "schuyler": {"county": "95", "supreme": "96"},
    "seneca": {"county": "97", "supreme": "98"},
    "st. lawrence": {"county": "87", "supreme": "88"},
    "steuben": {"county": "99", "supreme": "100"},
    "suffolk": {"county": "101", "supreme": "102"},
    "sullivan": {"county": "103", "supreme": "104"},
    "tioga": {"county": "105", "supreme": "106"},
    "tompkins": {"county": "107", "supreme": "108"},
    "ulster": {"county": "109", "supreme": "110"},
    "warren": {"county": "111", "supreme": "112"},
    "washington": {"county": "113", "supreme": "114"},
    "wayne": {"county": "115", "supreme": "116"},
    "westchester": {"county": "117", "supreme": "118"},
    "wyoming": {"county": "119", "supreme": "120"},
    "yates": {"county": "121", "supreme": "122"},
}


def _get_court_value(county: str) -> Optional[str]:
    """Look up the WebCivil Supreme court select value for a county."""
    county_lower = county.lower().strip()
    courts = COUNTY_COURT_VALUES.get(county_lower)
    if not courts:
        return None
    return courts.get("supreme") or courts.get("county")


def _is_local_index(index_number: str) -> bool:
    """Return True if *index_number* matches the Local Civil format."""
    return bool(_LOCAL_INDEX_RE.match(index_number.strip().upper()))


def _parse_local_index(index_number: str) -> Optional[dict[str, str]]:
    """Parse a Local Civil index number into its component parts.

    Returns a dict with keys ``case_type``, ``number``, ``year``, ``court``
    or *None* if the string doesn't match the expected format.
    """
    m = _LOCAL_INDEX_RE.match(index_number.strip().upper())
    if not m:
        return None
    return m.groupdict()


def _detect_captcha_intercept(html: str) -> bool:
    """Return True if the HTML is the Terms-of-Use / hCaptcha intercept page.

    Both webcivil and webcivilLocal use a server-side intercept that shows a
    Terms of Use page with an hCaptcha checkbox.  This is triggered by IP
    reputation (server IPs are more likely to see it than residential IPs).
    """
    lower = html.lower()
    return (
        "captcha-intercept-page" in lower
        or ("h-captcha" in lower and "terms of use" in lower)
        or ("hcaptcha" in lower and "terms of use" in lower)
        or ("i am human" in lower and ("hcaptcha" in lower or "h-captcha" in lower))
    )


# Known hCaptcha sitekey used by webcivilLocal submit buttons
_HCAPTCHA_SITEKEY = "6c824b97-caeb-4a2a-9144-db4f1c9f86d0"

# Regex to extract hCaptcha sitekey from HTML
_SITEKEY_RE = re.compile(r'data-sitekey=["\']([0-9a-f-]+)["\']')


def _detect_hcaptcha_in_response(html: str) -> Optional[str]:
    """Detect hCaptcha in a search response and return the sitekey if found.

    The webcivilLocal form uses an invisible hCaptcha widget on the submit
    button.  When curl_cffi POSTs without executing JS, the server returns
    an HTML page containing hCaptcha elements instead of search results.

    Returns the sitekey string if hCaptcha is detected, else None.
    """
    lower = html.lower()
    if "h-captcha" not in lower and "hcaptcha" not in lower:
        return None

    m = _SITEKEY_RE.search(html)
    if m:
        return m.group(1)

    # If we detect hCaptcha markers but can't extract sitekey, use the known one
    if "h-captcha" in lower or "hcaptcha" in lower:
        return _HCAPTCHA_SITEKEY

    return None


def _clean_text(text: Optional[str]) -> Optional[str]:
    """Clean whitespace from extracted text."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else None


def _parse_search_results_table(soup: BeautifulSoup) -> list[dict]:
    """Parse the search results table from WebCivil Supreme or Local.

    Supreme results contain links to ``FCASCaseDetail``.
    Local results contain links to ``LCCaseInfo``.
    """
    results = []

    all_links = soup.find_all("a")
    for link in all_links:
        href = link.get("href", "")
        # Accept both Supreme and Local detail links
        if "FCASCaseDetail" not in href and "LCCaseInfo" not in href:
            continue

        index_text = _clean_text(link.get_text())
        if not index_text:
            continue

        row = link.find_parent("tr")
        if not row:
            continue

        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        result: dict = {
            "detail_url": href,
            "index_number": index_text,
        }

        cell_texts = [_clean_text(cell.get_text()) for cell in cells]

        if len(cell_texts) >= 5:
            result["court_name"] = cell_texts[1]
            result["year"] = cell_texts[2]
            result["plaintiff"] = cell_texts[3]
            result["defendant"] = cell_texts[4]
        elif len(cell_texts) >= 3:
            result["court_name"] = cell_texts[1]
            result["plaintiff"] = cell_texts[2] if len(cell_texts) > 2 else None

        results.append(result)

    return results


def _parse_case_detail_page(soup: BeautifulSoup) -> dict:
    """Parse a case detail page from WebCivil."""
    detail: dict = {}

    all_text = soup.get_text(" ", strip=True)

    patterns = {
        "case_status": [
            r"(?:Case\s*)?Status\s*[:\-]\s*([^\n\r]+)",
            r"Disposition\s*[:\-]\s*([^\n\r]+)",
        ],
        "justice": [
            r"Justice\s*[:\-]\s*([^\n\r]+)",
            r"Judge\s*[:\-]\s*([^\n\r]+)",
            r"Assigned\s+Justice\s*[:\-]\s*([^\n\r]+)",
        ],
        "part": [
            r"Part\s*[:\-]\s*([^\n\r]+)",
            r"Calendar\s+Part\s*[:\-]\s*([^\n\r]+)",
        ],
    }

    for field_name, field_patterns in patterns.items():
        for pattern in field_patterns:
            match = re.search(pattern, all_text, re.IGNORECASE)
            if match:
                detail[field_name] = _clean_text(match.group(1))
                break

    rows = soup.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 2:
            label = _clean_text(cells[0].get_text())
            value = _clean_text(cells[1].get_text())
            if label and value:
                label_lower = label.lower().rstrip(":")
                if "plaintiff" in label_lower and "firm" in label_lower:
                    detail.setdefault("plaintiff_firm", value)
                elif "defendant" in label_lower and "firm" in label_lower:
                    detail.setdefault("defendant_firm", value)
                elif "plaintiff" in label_lower or "petitioner" in label_lower:
                    detail.setdefault("plaintiff", value)
                elif "defendant" in label_lower or "respondent" in label_lower:
                    detail.setdefault("defendant", value)
                elif label_lower in ("justice", "judge", "assigned justice"):
                    detail.setdefault("justice", value)
                elif label_lower in ("part", "calendar part"):
                    detail.setdefault("part", value)
                elif label_lower in ("status", "case status", "disposition"):
                    detail.setdefault("case_status", value)
                elif label_lower in ("index number", "index no", "case number"):
                    detail.setdefault("index_number", value)
                elif label_lower in ("county", "court"):
                    detail.setdefault("county", value)
                elif label_lower in ("filed", "year filed", "filing date"):
                    detail.setdefault("year_filed", value)

    detail["last_action"] = _extract_last_action(soup)
    detail["last_action_date"] = _extract_last_action_date(soup)

    return detail


def _extract_last_action(soup: BeautifulSoup) -> Optional[str]:
    """Extract the most recent court action/filing from the detail page."""
    text = soup.get_text(" ", strip=True)

    patterns = [
        r"(?:Last|Latest|Most Recent)\s+(?:Action|Filing|Motion)\s*[:\-]\s*([^\n\r]+)",
        r"Motion\s*#?\s*\d+\s*[:\-]?\s*([^\n\r]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return _clean_text(match.group(1))

    tables = soup.find_all("table")
    for table in tables:
        headers = table.find_all("th")
        header_texts = [_clean_text(h.get_text()) for h in headers]
        header_lower = [h.lower() if h else "" for h in header_texts]

        is_filing_table = any(
            keyword in " ".join(header_lower)
            for keyword in ["motion", "filing", "action", "sequence", "document"]
        )

        if is_filing_table:
            rows = table.find_all("tr")
            if len(rows) > 1:
                last_row = rows[-1]
                cells = last_row.find_all("td")
                if cells:
                    cell_texts = [_clean_text(c.get_text()) for c in cells]
                    action_text = " - ".join(t for t in cell_texts if t)
                    if action_text:
                        return action_text

    return None


def _extract_last_action_date(soup: BeautifulSoup) -> Optional[str]:
    """Extract the date of the most recent court action."""
    text = soup.get_text(" ", strip=True)

    patterns = [
        r"(?:Last|Latest|Most Recent)\s+(?:Action|Filing)\s+Date\s*[:\-]\s*(\d{1,2}/\d{1,2}/\d{2,4})",
        r"Filed\s*[:\-]?\s*(\d{1,2}/\d{1,2}/\d{2,4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def _parse_appearances_from_detail(soup: BeautifulSoup) -> list[dict]:
    """Extract appearance/calendar entries from a case detail page."""
    appearances = []

    tables = soup.find_all("table")
    for table in tables:
        headers = table.find_all("th")
        header_texts = [(_clean_text(h.get_text()) or "").lower() for h in headers]

        is_appearance_table = any(
            keyword in " ".join(header_texts)
            for keyword in ["appearance", "calendar", "scheduled"]
        )

        if not is_appearance_table:
            continue

        rows = table.find_all("tr")[1:]
        for row in rows:
            cells = row.find_all("td")
            if not cells:
                continue

            cell_texts = [_clean_text(c.get_text()) for c in cells]

            appearance: dict = {}
            for i, header_text in enumerate(header_texts):
                if i >= len(cell_texts):
                    break
                value = cell_texts[i]
                if not value:
                    continue

                if "date" in header_text:
                    appearance["date"] = value
                elif "time" in header_text:
                    appearance["time"] = value
                elif "type" in header_text or "reason" in header_text:
                    appearance["type"] = value
                elif "part" in header_text or "location" in header_text or "room" in header_text:
                    appearance["location"] = value
                elif "result" in header_text or "outcome" in header_text:
                    appearance["result"] = value

            if appearance.get("date"):
                appearances.append(appearance)

    return appearances


class NYWebCivilAdapter(CourtAdapter):
    """Adapter for NY WebCivil — Supreme *and* Local Civil courts.

    Supports two separate court systems on the same domain:

    * **WebCivil Supreme** (``/webcivil/FCASSearch``)
      Index numbers look like ``152847/2026``.
    * **WebCivil Local** (``/webcivilLocal/LCSearch``)
      Index numbers look like ``LT-332489-24/BX``.

    The adapter auto-detects which system to query based on the index number
    format and provides a two-tier scraping strategy:

    1. Primary — fast ``httpx``-based requests via :class:`ScraperEngine`.
    2. Fallback — ``curl_cffi`` with browser TLS impersonation via
       :class:`BrowserEngine` when the primary request fails (Cloudflare
       challenge, CAPTCHA, HTTP 403).
    3. Browserless — remote Chrome via :class:`BrowserlessEngine` with
       automatic CAPTCHA solving when curl_cffi also fails (hCaptcha gate).
    4. Captcha solver — :class:`CaptchaSolverEngine` uses a third-party
       human-solver service (2Captcha/CapSolver) as a last resort.

    If the server responds with a Terms-of-Use / hCaptcha intercept page
    (common for cloud/server IPs), the adapter first tries Browserless
    (remote Chrome with built-in CAPTCHA solving). If Browserless also
    fails (e.g. token rejected), it falls back to the captcha solver
    service for guaranteed human-solved tokens.
    """

    def __init__(self) -> None:
        self._engine: Optional[ScraperEngine] = None
        self._browser_engine: Optional[BrowserEngine] = None
        self._browserless_engine: Optional[BrowserlessEngine] = None
        self._captcha_solver_engine: Optional[CaptchaSolverEngine] = None

    def _get_engine(self) -> ScraperEngine:
        if self._engine is None:
            self._engine = ScraperEngine()
        return self._engine

    def _get_browser_engine(self) -> BrowserEngine:
        """Lazily create the headless browser engine for fallback scraping."""
        if self._browser_engine is None:
            self._browser_engine = BrowserEngine()
        return self._browser_engine

    def _get_browserless_engine(self) -> BrowserlessEngine:
        """Lazily create the Browserless engine for CAPTCHA-protected scraping."""
        if self._browserless_engine is None:
            self._browserless_engine = BrowserlessEngine()
        return self._browserless_engine

    def _get_captcha_solver_engine(self) -> CaptchaSolverEngine:
        """Lazily create the captcha solver engine for CAPTCHA-protected scraping."""
        if self._captcha_solver_engine is None:
            self._captcha_solver_engine = CaptchaSolverEngine()
        return self._captcha_solver_engine

    def _should_fallback(self, result: "ScrapeResult") -> bool:
        """Decide whether to retry the request with the headless browser."""
        if result.success:
            return False
        if result.cloudflare_detected or result.captcha_detected:
            return True
        if result.status_code == 403:
            return True
        return False

    @property
    def court_system(self) -> CourtSystem:
        return CourtSystem.NY_WEBCIVIL

    @property
    def display_name(self) -> str:
        return "NY WebCivil (Supreme & Local Civil)"

    @property
    def state(self) -> str:
        return "NY"

    # ------------------------------------------------------------------
    # Search entry-point
    # ------------------------------------------------------------------

    async def search(self, params: SearchParams) -> list[CourtRecord]:
        """Search NY WebCivil for cases by index number or party name.

        Automatically routes to the correct court system (Supreme vs Local)
        based on the index number format.
        """
        engine = self._get_engine()

        if params.index_number:
            # Auto-detect: Local Civil index numbers have a specific format
            if _is_local_index(params.index_number):
                return await self._search_local_by_index(engine, params)
            return await self._search_supreme_by_index(engine, params)
        elif params.plaintiff or params.defendant:
            return await self._search_by_party(engine, params)
        else:
            logger.warning("No search parameters provided for NYWebCivil search")
            return []

    # ------------------------------------------------------------------
    # Supreme Court — index search
    # ------------------------------------------------------------------

    async def _search_supreme_by_index(
        self, engine: ScraperEngine, params: SearchParams
    ) -> list[CourtRecord]:
        """Search WebCivil Supreme by index number."""
        search_url = f"{BASE_URL_SUPREME}/FCASSearch"

        form_data: dict[str, str] = {
            "txtIndex": params.index_number or "",
            "cboSort": "index_number",
            "rbOutputFormat": "H",
            "param": "I",
        }

        if params.county:
            court_value = _get_court_value(params.county)
            if court_value:
                form_data["cboCourt"] = court_value

        logger.info(
            "Searching WebCivil Supreme by index: %s (county: %s)",
            params.index_number,
            params.county,
        )

        result = await engine.post(search_url, data=form_data)

        if not result.success:
            if self._should_fallback(result):
                logger.info(
                    "httpx request failed (%s), retrying with browser fallback",
                    result.error_message,
                )
                result = await self._browser_search_supreme_index(params, form_data)
            else:
                if result.captcha_detected:
                    logger.warning("CAPTCHA blocked WebCivil Supreme index search")
                return []

        if not result.success or not result.soup:
            return []

        # Check for hCaptcha intercept page — try Browserless, then captcha solver
        if result.html and _detect_captcha_intercept(result.html):
            logger.info(
                "WebCivil Supreme returned hCaptcha intercept page — "
                "escalating to Browserless"
            )
            county_value = None
            if params.county:
                county_value = _get_court_value(params.county)
            bl_result = await self._browserless_search_supreme_index(
                params.index_number or "", county_value
            )
            if bl_result.success and bl_result.soup:
                return self._parse_search_results(bl_result.soup, params)
            # Browserless failed — fall back to captcha solver
            logger.info(
                "Browserless failed for Supreme search — "
                "falling back to captcha solver"
            )
            solver_result = await self._captcha_solver_search_supreme_index(
                params.index_number or "", county_value
            )
            if solver_result.success and solver_result.soup:
                return self._parse_search_results(solver_result.soup, params)
            return []

        return self._parse_search_results(result.soup, params)

    async def _browser_search_supreme_index(
        self,
        params: SearchParams,
        form_data: dict[str, str],
    ) -> "ScrapeResult":
        """Browser fallback for WebCivil Supreme index search.

        Tries curl_cffi first, then escalates to Browserless (remote Chrome
        with automatic CAPTCHA solving) if hCaptcha is detected. If Browserless
        also fails, falls back to captcha solver (2Captcha/CapSolver).
        """
        from app.scraper.engine import ScrapeResult

        browser = self._get_browser_engine()

        logger.info(
            "Browser fallback (Supreme): index %s (county: %s)",
            params.index_number,
            params.county,
        )

        try:
            form_page = await browser.get(SUPREME_INDEX_SEARCH_URL)
            if not form_page.success:
                logger.warning(
                    "Browser fallback: could not load Supreme index form (HTTP %s)",
                    form_page.status_code,
                )
                # curl_cffi couldn't load the form — try Browserless, then captcha solver
                county_value = None
                if params.county:
                    county_value = _get_court_value(params.county)
                return await self._browserless_or_solver_search_supreme(
                    params.index_number or "", county_value
                )

            post_data: dict[str, str] = {
                "hWhichPage": "I",
                "hCourtType": "Supreme",
                "hPageNumber": "1",
                "hSearchKey": "",
                "rbStatus": "open",
                "rbFutureCases": "N",
                "rbOutputFormat": "HTML",
                "cboSort": "index_number",
                "cboYearOfFiling": "0",
                "btnFindCase": "Find Case(s)",
            }
            post_data.update(form_data)

            result = await browser.post_form(
                url=f"{BASE_URL_SUPREME}/FCASSearch", data=post_data
            )

            # Detect hCaptcha intercept — escalate to Browserless, then captcha solver
            if result.success and result.html and _detect_captcha_intercept(result.html):
                logger.info(
                    "curl_cffi hit hCaptcha for Supreme search — "
                    "escalating to Browserless"
                )
                county_value = None
                if params.county:
                    county_value = _get_court_value(params.county)
                return await self._browserless_or_solver_search_supreme(
                    params.index_number or "", county_value
                )

            return result
        except Exception as exc:
            logger.error("Browser fallback failed for Supreme index search: %s", exc)
            # Last resort: try Browserless, then captcha solver
            county_value = None
            if params.county:
                county_value = _get_court_value(params.county)
            return await self._browserless_or_solver_search_supreme(
                params.index_number or "", county_value
            )

    async def _browserless_search_supreme_index(
        self,
        index_number: str,
        county_court_value: Optional[str] = None,
    ) -> "ScrapeResult":
        """Use Browserless remote Chrome to search Supreme with auto CAPTCHA solving."""
        browserless = self._get_browserless_engine()
        logger.info(
            "Browserless fallback (Supreme): %s", index_number
        )
        return await browserless.search_supreme_by_index(
            index_number=index_number,
            county_court_value=county_court_value,
        )

    async def _captcha_solver_search_supreme_index(
        self,
        index_number: str,
        county_court_value: Optional[str] = None,
    ) -> "ScrapeResult":
        """Use captcha solver (2Captcha/CapSolver) to search Supreme."""
        solver = self._get_captcha_solver_engine()
        logger.info(
            "Captcha solver fallback (Supreme): %s", index_number
        )
        return await solver.search_supreme_by_index(
            index_number=index_number,
            county_court_value=county_court_value,
        )

    async def _browserless_or_solver_search_supreme(
        self,
        index_number: str,
        county_court_value: Optional[str] = None,
    ) -> "ScrapeResult":
        """Try Browserless first, then fall back to captcha solver for Supreme."""
        bl_result = await self._browserless_search_supreme_index(
            index_number, county_court_value
        )
        if bl_result.success:
            return bl_result
        logger.info(
            "Browserless failed for Supreme search — "
            "falling back to captcha solver"
        )
        return await self._captcha_solver_search_supreme_index(
            index_number, county_court_value
        )

    # ------------------------------------------------------------------
    # Local Civil Court — index search
    # ------------------------------------------------------------------

    async def _search_local_by_index(
        self, engine: ScraperEngine, params: SearchParams
    ) -> list[CourtRecord]:
        """Search WebCivil Local by index number (e.g. LT-332489-24/BX).

        If *params.captcha_token* is provided, it is included in the POST as
        ``h-captcha-response`` and ``g-recaptcha-response`` fields so that
        the server accepts the submission.

        When hCaptcha blocks the search, escalates to the captcha solver
        service for automatic CAPTCHA solving instead of requiring manual
        user intervention.
        """
        parsed = _parse_local_index(params.index_number or "")
        if not parsed:
            logger.warning(
                "Could not parse local index number: %s", params.index_number
            )
            return []

        search_url = f"{BASE_URL_LOCAL}/LCSearch"

        form_data: dict[str, str] = {
            "hWhichPage": "I",
            "hCourtType": "Local",
            "hPageNumber": "1",
            "hSearchKey": "",
            "cboCaseType": parsed["case_type"],
            "txtIndexNumber": parsed["number"],
            "txtIndexYear": parsed["year"],
            "cboIndexCourtIndicator": parsed["court"],
            "cboSort": "court",
            "rbOutputFormat": "HTML",
            "btnFindCase": "Find Case(s)",
        }

        # Include user-solved hCaptcha token when available
        if params.captcha_token:
            form_data["h-captcha-response"] = params.captcha_token
            form_data["g-recaptcha-response"] = params.captcha_token
            logger.info(
                "Including user-provided hCaptcha token in Local search POST"
            )

        logger.info(
            "Searching WebCivil Local by index: %s "
            "(type=%s, number=%s, year=%s, court=%s)",
            params.index_number,
            parsed["case_type"],
            parsed["number"],
            parsed["year"],
            parsed["court"],
        )

        # Try httpx first
        result = await engine.post(search_url, data=form_data)

        if not result.success:
            if self._should_fallback(result):
                logger.info(
                    "httpx request failed (%s), retrying Local search with browser",
                    result.error_message,
                )
                # _browser_search_local_index raises CaptchaRequiredError
                # if hCaptcha is detected, so no need to check here.
                result = await self._browser_search_local_index(
                    params, form_data, parsed
                )
            else:
                if result.captcha_detected:
                    logger.warning("CAPTCHA blocked WebCivil Local index search")
                return []

        if not result.success or not result.soup:
            return []

        # Check for hCaptcha intercept (server-side "I am human" page)
        # or invisible hCaptcha — try Browserless, then captcha solver
        captcha_blocked = False
        if result.html and _detect_captcha_intercept(result.html):
            logger.info(
                "WebCivil Local returned hCaptcha intercept page — "
                "escalating to Browserless"
            )
            captcha_blocked = True
        elif result.html:
            sitekey = _detect_hcaptcha_in_response(result.html)
            if sitekey and "LCCaseInfo" not in result.html:
                logger.info(
                    "WebCivil Local response contains hCaptcha — "
                    "escalating to Browserless"
                )
                captcha_blocked = True

        if captcha_blocked:
            fallback_result = await self._browserless_or_solver_search_local(parsed)
            if fallback_result.success and fallback_result.soup:
                return self._parse_search_results(
                    fallback_result.soup, params, is_local=True
                )
            return []

        return self._parse_search_results(result.soup, params, is_local=True)

    async def _browser_search_local_index(
        self,
        params: SearchParams,
        form_data: dict[str, str],
        parsed: dict[str, str],
    ) -> "ScrapeResult":
        """Browser fallback for WebCivil Local index search.

        Tries curl_cffi first, then escalates to Browserless (remote Chrome
        with automatic CAPTCHA solving) if hCaptcha is detected. If Browserless
        also fails, falls back to captcha solver (2Captcha/CapSolver).
        """
        from app.scraper.engine import ScrapeResult

        browser = self._get_browser_engine()

        logger.info(
            "Browser fallback (Local): index %s", params.index_number
        )

        try:
            form_page = await browser.get(LOCAL_INDEX_SEARCH_URL)
            if not form_page.success:
                logger.warning(
                    "Browser fallback: could not load Local index form (HTTP %s)",
                    form_page.status_code,
                )
                # curl_cffi couldn't even load the form — try Browserless, then captcha solver
                return await self._browserless_or_solver_search_local(parsed)

            result = await browser.post_form(
                url=f"{BASE_URL_LOCAL}/LCSearch", data=form_data
            )

            # Detect hCaptcha intercept — escalate to Browserless, then captcha solver
            captcha_blocked = False
            if result.success and result.html and _detect_captcha_intercept(result.html):
                captcha_blocked = True
            elif result.success and result.html:
                sitekey = _detect_hcaptcha_in_response(result.html)
                if sitekey and "LCCaseInfo" not in result.html:
                    captcha_blocked = True

            if captcha_blocked:
                logger.info(
                    "curl_cffi hit hCaptcha for Local search — "
                    "escalating to Browserless"
                )
                return await self._browserless_or_solver_search_local(parsed)

            return result
        except Exception as exc:
            logger.error("Browser fallback failed for Local index search: %s", exc)
            # Last resort: try Browserless, then captcha solver
            return await self._browserless_or_solver_search_local(parsed)

    async def _browserless_search_local_index(
        self,
        parsed: dict[str, str],
    ) -> "ScrapeResult":
        """Use Browserless remote Chrome to search Local with auto CAPTCHA solving."""
        browserless = self._get_browserless_engine()
        logger.info(
            "Browserless fallback (Local): %s-%s-%s/%s",
            parsed["case_type"], parsed["number"],
            parsed["year"], parsed["court"],
        )
        return await browserless.search_local_by_index(
            case_type=parsed["case_type"],
            number=parsed["number"],
            year=parsed["year"],
            court=parsed["court"],
        )

    async def _captcha_solver_search_local_index(
        self,
        parsed: dict[str, str],
    ) -> "ScrapeResult":
        """Use captcha solver (2Captcha/CapSolver) to search Local."""
        solver = self._get_captcha_solver_engine()
        logger.info(
            "Captcha solver fallback (Local): %s-%s-%s/%s",
            parsed["case_type"], parsed["number"],
            parsed["year"], parsed["court"],
        )
        return await solver.search_local_by_index(
            case_type=parsed["case_type"],
            number=parsed["number"],
            year=parsed["year"],
            court=parsed["court"],
        )

    async def _browserless_or_solver_search_local(
        self,
        parsed: dict[str, str],
    ) -> "ScrapeResult":
        """Try Browserless first, then fall back to captcha solver for Local."""
        bl_result = await self._browserless_search_local_index(parsed)
        if bl_result.success:
            return bl_result
        logger.info(
            "Browserless failed for Local search — "
            "falling back to captcha solver"
        )
        return await self._captcha_solver_search_local_index(parsed)

    # ------------------------------------------------------------------
    # Party search (Supreme only for now)
    # ------------------------------------------------------------------

    async def _search_by_party(
        self, engine: ScraperEngine, params: SearchParams
    ) -> list[CourtRecord]:
        """Search by party name, falling back to headless browser on failure."""
        search_url = f"{BASE_URL_SUPREME}/FCASSearch"

        form_data: dict[str, str] = {
            "cboSort": "index_number",
            "rbOutputFormat": "H",
            "param": "P",
        }

        if params.plaintiff:
            form_data["txtPlaintiff"] = params.plaintiff
        if params.defendant:
            form_data["txtDefendant"] = params.defendant

        if params.county:
            court_value = _get_court_value(params.county)
            if court_value:
                form_data["cboCourt"] = court_value

        logger.info(
            "Searching NYWebCivil by party: plaintiff=%s defendant=%s",
            params.plaintiff,
            params.defendant,
        )

        result = await engine.post(search_url, data=form_data)

        if not result.success:
            if self._should_fallback(result):
                logger.info(
                    "httpx request failed (%s), retrying party search with browser",
                    result.error_message,
                )
                result = await self._browser_search_party(params, form_data)
            else:
                if result.captcha_detected:
                    logger.warning("CAPTCHA blocked NYWebCivil party search")
                return []

        if not result.success or not result.soup:
            return []

        # Check for hCaptcha intercept
        if result.html and _detect_captcha_intercept(result.html):
            logger.warning(
                "WebCivil Supreme returned hCaptcha intercept on party search"
            )
            return []

        return self._parse_search_results(result.soup, params)

    async def _browser_search_party(
        self,
        params: SearchParams,
        form_data: dict[str, str],
    ) -> "ScrapeResult":
        """Browser fallback for party-name search."""
        from app.scraper.engine import ScrapeResult

        browser = self._get_browser_engine()

        logger.info(
            "Browser fallback: party search plaintiff=%s defendant=%s",
            params.plaintiff,
            params.defendant,
        )

        try:
            form_page = await browser.get(SUPREME_PARTY_SEARCH_URL)
            if not form_page.success:
                logger.warning(
                    "Browser fallback: could not load party search form (HTTP %s)",
                    form_page.status_code,
                )
                return form_page

            post_data: dict[str, str] = {
                "hWhichPage": "P",
                "hCourtType": "Supreme",
                "hPageNumber": "1",
                "hSearchKey": "",
                "rbStatus": "open",
                "rbFutureCases": "N",
                "rbOutputFormat": "HTML",
                "cboSort": "index_number",
                "cboYearOfFiling": "0",
                "btnFindCase": "Find Case(s)",
            }
            post_data.update(form_data)

            result = await browser.post_form(
                url=f"{BASE_URL_SUPREME}/FCASSearch", data=post_data
            )

            if result.success and result.html and _detect_captcha_intercept(result.html):
                logger.warning("Browser fallback: hCaptcha intercept on party search")
                return ScrapeResult(
                    success=False,
                    html=result.html,
                    status_code=result.status_code,
                    error_message="hCaptcha intercept — search blocked by server",
                    captcha_detected=True,
                )

            return result
        except Exception as exc:
            logger.error("Browser fallback failed for party search: %s", exc)
            return ScrapeResult(
                success=False,
                error_message=f"Browser fallback error: {exc}",
            )

    # ------------------------------------------------------------------
    # Result parsing
    # ------------------------------------------------------------------

    def _parse_search_results(
        self, soup: BeautifulSoup, params: SearchParams, *, is_local: bool = False
    ) -> list[CourtRecord]:
        """Parse search results page into CourtRecord objects."""
        raw_results = _parse_search_results_table(soup)

        records = []
        for raw in raw_results:
            case_year = None
            year_str = raw.get("year")
            if year_str:
                year_match = re.search(r"\d{4}", year_str)
                if year_match:
                    try:
                        case_year = int(year_match.group())
                    except ValueError:
                        pass

            county = params.county or ""
            court_name = raw.get("court_name", "")
            if court_name:
                county_match = re.match(
                    r"(\w[\w\s.]+?)(?:\s+(?:Supreme|County|Civil|Housing)\s+Court)",
                    court_name,
                )
                if county_match:
                    county = county_match.group(1).strip()

            # Determine court_type from context
            court_type = params.court_type or ("local_civil" if is_local else "supreme")

            record = CourtRecord(
                index_number=raw.get("index_number", ""),
                court_type=court_type,
                county=county,
                case_year=case_year,
                plaintiff=raw.get("plaintiff"),
                defendant=raw.get("defendant"),
                source=CaseSource.WEBCIVIL_SCRAPER,
                raw_data=raw,
            )
            records.append(record)

        logger.info("NYWebCivil search returned %d results", len(records))
        return records

    # ------------------------------------------------------------------
    # Case details
    # ------------------------------------------------------------------

    def _base_url_for_detail(self, detail_url: str) -> str:
        """Return the correct base URL depending on the detail link target."""
        if "LCCaseInfo" in detail_url:
            return BASE_URL_LOCAL
        return BASE_URL_SUPREME

    async def get_case_details(
        self, index_number: str, court_type: str, county: str
    ) -> Optional[CourtRecord]:
        """Fetch full details for a specific case from NY WebCivil."""
        engine = self._get_engine()

        params = SearchParams(
            index_number=index_number,
            court_type=court_type,
            county=county,
        )
        search_results = await self.search(params)

        if not search_results:
            logger.info("No results found for case %s", index_number)
            return None

        record = search_results[0]

        detail_url = record.raw_data.get("detail_url") if record.raw_data else None
        if detail_url:
            base = self._base_url_for_detail(detail_url)
            if not detail_url.startswith("http"):
                detail_url = f"{base}/{detail_url}"

            detail_result = await engine.get(detail_url)

            # Fallback to browser if httpx is blocked
            if not detail_result.success and self._should_fallback(detail_result):
                browser = self._get_browser_engine()
                detail_result = await browser.get(detail_url)

            if detail_result.success and detail_result.soup:
                detail_data = _parse_case_detail_page(detail_result.soup)

                record.case_status = detail_data.get("case_status") or record.case_status
                record.plaintiff = detail_data.get("plaintiff") or record.plaintiff
                record.defendant = detail_data.get("defendant") or record.defendant
                record.plaintiff_firm = detail_data.get("plaintiff_firm")
                record.defendant_firm = detail_data.get("defendant_firm")
                record.justice = detail_data.get("justice")
                record.part = detail_data.get("part")
                record.last_action = detail_data.get("last_action")
                record.last_action_date = detail_data.get("last_action_date")

        return record

    # ------------------------------------------------------------------
    # Appearances
    # ------------------------------------------------------------------

    async def get_appearances(
        self, index_number: str, court_type: str, county: str
    ) -> list[AppearanceRecord]:
        """Fetch all scheduled appearances for a case."""
        engine = self._get_engine()

        params = SearchParams(
            index_number=index_number,
            court_type=court_type,
            county=county,
        )

        search_results = await self.search(params)
        if not search_results:
            return []

        record = search_results[0]
        detail_url = record.raw_data.get("detail_url") if record.raw_data else None

        if not detail_url:
            return []

        base = self._base_url_for_detail(detail_url)
        if not detail_url.startswith("http"):
            detail_url = f"{base}/{detail_url}"

        detail_result = await engine.get(detail_url)

        # Fallback to browser if httpx is blocked
        if not detail_result.success and self._should_fallback(detail_result):
            browser = self._get_browser_engine()
            detail_result = await browser.get(detail_url)

        if not detail_result.success or not detail_result.soup:
            return []

        raw_appearances = _parse_appearances_from_detail(detail_result.soup)

        appearances = []
        for raw in raw_appearances:
            date_str = raw.get("date")
            if not date_str:
                continue

            appearance_date = None
            for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
                try:
                    appearance_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue

            if not appearance_date:
                continue

            appearances.append(AppearanceRecord(
                appearance_date=appearance_date,
                appearance_time=raw.get("time"),
                appearance_type=raw.get("type"),
                location=raw.get("location"),
                notes=raw.get("result"),
                source=CaseSource.WEBCIVIL_SCRAPER,
            ))

        logger.info(
            "Found %d appearances for case %s", len(appearances), index_number
        )
        return appearances

    # ------------------------------------------------------------------
    # Attorney search
    # ------------------------------------------------------------------

    async def search_by_attorney(
        self, attorney_name: str, attorney_reg_number: Optional[str] = None, county: Optional[str] = None
    ) -> list[CourtRecord]:
        """Search NY WebCivil for cases associated with an attorney."""
        engine = self._get_engine()
        all_records: list[CourtRecord] = []

        params_plaintiff = SearchParams(
            plaintiff=attorney_name,
            county=county,
        )
        results_p = await self._search_by_party(engine, params_plaintiff)
        all_records.extend(results_p)

        params_defendant = SearchParams(
            defendant=attorney_name,
            county=county,
        )
        results_d = await self._search_by_party(engine, params_defendant)

        seen = {r.index_number for r in all_records}
        for r in results_d:
            if r.index_number not in seen:
                all_records.append(r)
                seen.add(r.index_number)

        logger.info(
            "NYWebCivil attorney search for '%s' found %d cases",
            attorney_name, len(all_records),
        )
        return all_records

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Check if NY WebCivil is accessible."""
        engine = self._get_engine()
        return await engine.health_check(f"{BASE_URL_SUPREME}/FCASMain")
