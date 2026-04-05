"""
Abstract base classes for court adapters and data sources.

These interfaces define the contract that all court system integrations
must implement, enabling the app to support multiple courts and states.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import date, datetime


class CaseSource(str, Enum):
    """Identifies the origin of case data."""
    MANUAL = "manual"
    WEBCIVIL_SCRAPER = "webcivil_scraper"
    WEBCRIMIN_SCRAPER = "webcrimin_scraper"
    ETRACK_EMAIL = "etrack_email"
    API_PROVIDER = "api_provider"


class CourtSystem(str, Enum):
    """Supported court systems."""
    NY_WEBCIVIL = "ny_webcivil"
    NY_WEBCRIMIN = "ny_webcrimin"


@dataclass
class CourtRecord:
    """Normalized case record from any court source."""
    index_number: str
    court_type: str
    county: str
    case_year: Optional[int] = None
    case_status: Optional[str] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defendant_firm: Optional[str] = None
    justice: Optional[str] = None
    part: Optional[str] = None
    last_action: Optional[str] = None
    last_action_date: Optional[str] = None
    source: CaseSource = CaseSource.MANUAL
    raw_data: Optional[dict] = field(default_factory=dict)


@dataclass
class AppearanceRecord:
    """Normalized appearance record from any court source."""
    appearance_date: date
    appearance_time: Optional[str] = None
    appearance_type: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    source: CaseSource = CaseSource.MANUAL


@dataclass
class SearchParams:
    """Parameters for searching a court system."""
    index_number: Optional[str] = None
    court_type: Optional[str] = None
    county: Optional[str] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    attorney_name: Optional[str] = None
    state: str = "NY"


class CourtAdapter(ABC):
    """
    Abstract interface for court system integrations.

    Each court system (NY WebCivil, NY WebCriminal, CA Courts, etc.)
    implements this interface to provide search, case details, and
    appearance data in a normalized format.
    """

    @property
    @abstractmethod
    def court_system(self) -> CourtSystem:
        """Return the court system identifier."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name for this court system."""
        ...

    @property
    @abstractmethod
    def state(self) -> str:
        """Two-letter state code."""
        ...

    @abstractmethod
    async def search(self, params: SearchParams) -> list[CourtRecord]:
        """
        Search the court system for cases matching the given parameters.
        Returns a list of matching case records for the user to verify.
        """
        ...

    @abstractmethod
    async def get_case_details(self, index_number: str, court_type: str, county: str) -> Optional[CourtRecord]:
        """
        Fetch full details for a specific case.
        Used for verification and periodic updates.
        """
        ...

    @abstractmethod
    async def get_appearances(self, index_number: str, court_type: str, county: str) -> list[AppearanceRecord]:
        """
        Fetch all scheduled appearances for a case.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the court system is accessible.
        Returns True if the adapter can connect successfully.
        """
        ...


class DataSource(ABC):
    """
    Abstract interface for data import methods.

    Each import method (scraper, email, API) implements this interface
    to provide case updates to the system.
    """

    @property
    @abstractmethod
    def source_type(self) -> CaseSource:
        """Return the data source type."""
        ...

    @abstractmethod
    async def fetch_updates(self, case_id: int, search_params: dict) -> Optional[CourtRecord]:
        """
        Fetch the latest data for a tracked case.
        Returns updated case record or None if no changes.
        """
        ...

    @abstractmethod
    async def parse_data(self, raw_data: dict) -> Optional[CourtRecord]:
        """
        Parse raw data (e.g., email content, API response) into a CourtRecord.
        """
        ...
