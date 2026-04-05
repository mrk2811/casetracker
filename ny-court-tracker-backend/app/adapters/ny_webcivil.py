"""
NY WebCivil adapter stub.

This adapter will be fully implemented in Phase 2 (scraper engine).
For now, it provides the interface and returns mock/placeholder data
for the case verification flow.
"""

from typing import Optional

from app.adapters.base import (
    CourtAdapter,
    CourtRecord,
    AppearanceRecord,
    SearchParams,
    CaseSource,
    CourtSystem,
)


class NYWebCivilAdapter(CourtAdapter):
    """
    Adapter for NY WebCivil (Supreme & Civil Courts).
    Covers Supreme Court, Civil Court, and Housing Court cases.
    Base URL: https://iapps.courts.state.ny.us/webcivil
    """

    @property
    def court_system(self) -> CourtSystem:
        return CourtSystem.NY_WEBCIVIL

    @property
    def display_name(self) -> str:
        return "NY WebCivil (Supreme & Civil)"

    @property
    def state(self) -> str:
        return "NY"

    async def search(self, params: SearchParams) -> list[CourtRecord]:
        """
        Search NY WebCivil for cases matching the given parameters.

        Phase 2 will implement actual scraping via headless Selenium.
        For now, returns an empty list. The manual entry flow still works.
        """
        # TODO Phase 2: Implement Selenium-based scraper
        # - Navigate to https://iapps.courts.state.ny.us/webcivil/FCASSearch
        # - Fill in search parameters (index number, county, court type)
        # - Parse results table
        # - Handle CAPTCHAs (flag and fall back to email)
        return []

    async def get_case_details(
        self, index_number: str, court_type: str, county: str
    ) -> Optional[CourtRecord]:
        """
        Fetch full details for a specific case from NY WebCivil.

        Phase 2 will implement actual scraping.
        For now, returns None (case not found via scraper).
        """
        # TODO Phase 2: Implement case detail scraping
        return None

    async def get_appearances(
        self, index_number: str, court_type: str, county: str
    ) -> list[AppearanceRecord]:
        """
        Fetch all scheduled appearances for a case from NY WebCivil.

        Phase 2 will implement actual scraping.
        """
        # TODO Phase 2: Implement appearance scraping
        return []

    async def health_check(self) -> bool:
        """
        Check if NY WebCivil is accessible.

        Phase 2 will implement an actual HTTP check.
        """
        # TODO Phase 2: Implement health check (HEAD request to base URL)
        return False
