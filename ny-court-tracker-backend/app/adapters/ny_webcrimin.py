"""
NY WebCriminal adapter - scrapes iapps.courts.state.ny.us/webcrimin.

Implements search by defendant name, case detail parsing,
appearance extraction, and health checks for the NY WebCriminal system.
"""

import logging
import re
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

from app.adapters.base import (
    CourtAdapter,
    CourtRecord,
    AppearanceRecord,
    SearchParams,
    CaseSource,
    CourtSystem,
)
from app.scraper.engine import ScraperEngine

logger = logging.getLogger(__name__)

BASE_URL = "https://iapps.courts.state.ny.us/webcrimin"


def _clean_text(text: Optional[str]) -> Optional[str]:
    """Clean whitespace from extracted text."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else None


def _parse_search_results(soup: BeautifulSoup) -> list[dict]:
    """Parse search results from WebCriminal."""
    results = []

    all_links = soup.find_all("a")
    for link in all_links:
        href = link.get("href", "")
        if "CaseDetail" not in href:
            continue

        link_text = _clean_text(link.get_text())
        if not link_text:
            continue

        row = link.find_parent("tr")
        if not row:
            continue

        cells = row.find_all("td")
        if len(cells) < 2:
            continue

        result: dict = {
            "detail_url": href,
            "case_number": link_text,
        }

        cell_texts = [_clean_text(cell.get_text()) for cell in cells]

        if len(cell_texts) >= 4:
            result["defendant"] = cell_texts[1]
            result["court_name"] = cell_texts[2]
            result["charges"] = cell_texts[3]
        elif len(cell_texts) >= 2:
            result["defendant"] = cell_texts[1]

        results.append(result)

    return results


def _parse_case_detail(soup: BeautifulSoup) -> dict:
    """Parse a criminal case detail page."""
    detail: dict = {}

    rows = soup.find_all("tr")
    for row in rows:
        cells = row.find_all("td")
        if len(cells) >= 2:
            label = _clean_text(cells[0].get_text())
            value = _clean_text(cells[1].get_text())
            if label and value:
                label_lower = label.lower().rstrip(":")
                if label_lower in ("defendant", "defendant name"):
                    detail.setdefault("defendant", value)
                elif label_lower in ("case number", "docket number", "indictment"):
                    detail.setdefault("case_number", value)
                elif label_lower in ("court", "court name"):
                    detail.setdefault("court_name", value)
                elif label_lower in ("county",):
                    detail.setdefault("county", value)
                elif label_lower in ("judge", "justice"):
                    detail.setdefault("justice", value)
                elif label_lower in ("status", "case status", "disposition"):
                    detail.setdefault("case_status", value)
                elif "charge" in label_lower:
                    detail.setdefault("charges", value)
                elif label_lower in ("arrest date", "filing date"):
                    detail.setdefault("filing_date", value)
                elif label_lower in ("next appearance", "next court date"):
                    detail.setdefault("next_appearance", value)
                elif "attorney" in label_lower or "counsel" in label_lower:
                    detail.setdefault("attorney", value)

    # Extract last action
    text = soup.get_text(" ", strip=True)
    patterns = [
        r"(?:Last|Latest|Most Recent)\s+(?:Action|Activity)\s*[:\-]\s*([^\n\r]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            detail["last_action"] = _clean_text(match.group(1))
            break

    return detail


def _parse_appearances(soup: BeautifulSoup) -> list[dict]:
    """Extract appearances from criminal case detail page."""
    appearances = []

    tables = soup.find_all("table")
    for table in tables:
        headers = table.find_all("th")
        header_texts = [(_clean_text(h.get_text()) or "").lower() for h in headers]

        is_appearance_table = any(
            keyword in " ".join(header_texts)
            for keyword in ["appearance", "calendar", "date", "scheduled", "adjournment"]
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
                elif "type" in header_text or "reason" in header_text or "purpose" in header_text:
                    appearance["type"] = value
                elif "part" in header_text or "location" in header_text or "room" in header_text:
                    appearance["location"] = value
                elif "result" in header_text or "outcome" in header_text:
                    appearance["result"] = value

            if appearance.get("date"):
                appearances.append(appearance)

    return appearances


class NYWebCriminAdapter(CourtAdapter):
    """
    Adapter for NY WebCriminal.
    Base URL: https://iapps.courts.state.ny.us/webcrimin
    """

    def __init__(self) -> None:
        self._engine: Optional[ScraperEngine] = None

    def _get_engine(self) -> ScraperEngine:
        if self._engine is None:
            self._engine = ScraperEngine()
        return self._engine

    @property
    def court_system(self) -> CourtSystem:
        return CourtSystem.NY_WEBCRIMIN

    @property
    def display_name(self) -> str:
        return "NY WebCriminal"

    @property
    def state(self) -> str:
        return "NY"

    async def search(self, params: SearchParams) -> list[CourtRecord]:
        """Search NY WebCriminal for cases."""
        engine = self._get_engine()

        search_url = f"{BASE_URL}/CRSearch"

        form_data: dict[str, str] = {}

        if params.index_number:
            form_data["txtCaseNumber"] = params.index_number
        if params.defendant:
            form_data["txtDefendant"] = params.defendant
        if params.county:
            form_data["txtCounty"] = params.county

        if not form_data:
            logger.warning("No search parameters provided for NYWebCriminal search")
            return []

        logger.info(
            "Searching NYWebCriminal: case=%s defendant=%s county=%s",
            params.index_number,
            params.defendant,
            params.county,
        )

        result = await engine.post(search_url, data=form_data)

        if not result.success:
            if result.captcha_detected:
                logger.warning("CAPTCHA blocked NYWebCriminal search")
            return []

        if not result.soup:
            return []

        raw_results = _parse_search_results(result.soup)

        records = []
        for raw in raw_results:
            record = CourtRecord(
                index_number=raw.get("case_number", ""),
                court_type="criminal",
                county=params.county or "",
                plaintiff="People of the State of New York",
                defendant=raw.get("defendant"),
                source=CaseSource.WEBCRIMIN_SCRAPER,
                raw_data=raw,
            )
            records.append(record)

        logger.info("NYWebCriminal search returned %d results", len(records))
        return records

    async def get_case_details(
        self, index_number: str, court_type: str, county: str
    ) -> Optional[CourtRecord]:
        """Fetch full details for a criminal case."""
        engine = self._get_engine()

        params = SearchParams(
            index_number=index_number,
            court_type=court_type,
            county=county,
        )
        search_results = await self.search(params)

        if not search_results:
            logger.info("No results found for criminal case %s", index_number)
            return None

        record = search_results[0]

        detail_url = record.raw_data.get("detail_url") if record.raw_data else None
        if detail_url:
            if not detail_url.startswith("http"):
                detail_url = f"{BASE_URL}/{detail_url}"

            detail_result = await engine.get(detail_url)
            if detail_result.success and detail_result.soup:
                detail_data = _parse_case_detail(detail_result.soup)

                record.case_status = detail_data.get("case_status") or record.case_status
                record.defendant = detail_data.get("defendant") or record.defendant
                record.justice = detail_data.get("justice")
                record.last_action = detail_data.get("last_action")

        return record

    async def get_appearances(
        self, index_number: str, court_type: str, county: str
    ) -> list[AppearanceRecord]:
        """Fetch all scheduled appearances for a criminal case."""
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

        if not detail_url.startswith("http"):
            detail_url = f"{BASE_URL}/{detail_url}"

        detail_result = await engine.get(detail_url)
        if not detail_result.success or not detail_result.soup:
            return []

        raw_appearances = _parse_appearances(detail_result.soup)

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
                source=CaseSource.WEBCRIMIN_SCRAPER,
            ))

        logger.info(
            "Found %d appearances for criminal case %s", len(appearances), index_number
        )
        return appearances

    async def health_check(self) -> bool:
        """Check if NY WebCriminal is accessible."""
        engine = self._get_engine()
        return await engine.health_check(f"{BASE_URL}/CRMain")
