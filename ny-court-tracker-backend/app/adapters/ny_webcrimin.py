"""
NY WebCriminal adapter stub.

This adapter will be fully implemented in Phase 2 (scraper engine).
For now, it provides the interface and returns mock/placeholder data.
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


class NYWebCriminAdapter(CourtAdapter):
    """
    Adapter for NY WebCriminal.
    Base URL: https://iapps.courts.state.ny.us/webcrimin
    """

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
        """
        Search NY WebCriminal for cases matching the given parameters.

        Phase 2 will implement actual scraping via headless Selenium.
        """
        # TODO Phase 2: Implement Selenium-based scraper
        return []

    async def get_case_details(
        self, index_number: str, court_type: str, county: str
    ) -> Optional[CourtRecord]:
        """
        Fetch full details for a specific case from NY WebCriminal.

        Phase 2 will implement actual scraping.
        """
        # TODO Phase 2: Implement case detail scraping
        return None

    async def get_appearances(
        self, index_number: str, court_type: str, county: str
    ) -> list[AppearanceRecord]:
        """
        Fetch all scheduled appearances for a case from NY WebCriminal.

        Phase 2 will implement actual scraping.
        """
        # TODO Phase 2: Implement appearance scraping
        return []

    async def health_check(self) -> bool:
        """
        Check if NY WebCriminal is accessible.

        Phase 2 will implement an actual HTTP check.
        """
        # TODO Phase 2: Implement health check
        return False
