from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date


# ─── Auth ───
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    attorney_reg_number: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    attorney_reg_number: Optional[str] = None
    created_at: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Freshness ───
class FreshnessInfo(BaseModel):
    """Freshness indicator data for a case."""
    last_checked_at: Optional[str] = None
    last_source: Optional[str] = None
    hours_since_check: Optional[float] = None
    status: str = "unknown"  # fresh (< 6hr), stale (< 24hr), outdated (> 24hr), unknown


# ─── Cases ───
class CaseCreate(BaseModel):
    court_type: str  # supreme, local_civil, criminal
    county: str
    index_number: str
    case_year: Optional[int] = None
    case_status: str = "active"
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defendant_firm: Optional[str] = None
    justice: Optional[str] = None
    part: Optional[str] = None
    notes: Optional[str] = None
    priority: str = "normal"
    source: str = "manual"
    court_system: Optional[str] = None
    search_params: Optional[str] = None
    verified: bool = False


class CaseUpdate(BaseModel):
    court_type: Optional[str] = None
    county: Optional[str] = None
    index_number: Optional[str] = None
    case_year: Optional[int] = None
    case_status: Optional[str] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defendant_firm: Optional[str] = None
    justice: Optional[str] = None
    part: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[str] = None


class CaseOut(BaseModel):
    id: int
    user_id: int
    court_type: str
    county: str
    index_number: str
    case_year: Optional[int] = None
    case_status: str
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defendant_firm: Optional[str] = None
    justice: Optional[str] = None
    part: Optional[str] = None
    notes: Optional[str] = None
    priority: str = "normal"
    source: str = "manual"
    last_checked_at: Optional[str] = None
    last_source: Optional[str] = None
    verified: bool = False
    court_system: Optional[str] = None
    created_at: str
    updated_at: str
    next_appearance: Optional[str] = None
    freshness: Optional[FreshnessInfo] = None


# ─── Case Verification ───
class CaseSearchRequest(BaseModel):
    """Request to search court system for case verification."""
    index_number: str
    court_type: str
    county: str
    court_system: str = "ny_webcivil"


class CaseSearchResult(BaseModel):
    """A single case result from court system search."""
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
    source: str = "manual"


class CaseSearchResponse(BaseModel):
    """Response from case search for verification."""
    results: list[CaseSearchResult]
    court_system: str
    message: str


class CaseVerifyRequest(BaseModel):
    """Confirm a case from search results and start tracking it."""
    index_number: str
    court_type: str
    county: str
    case_year: Optional[int] = None
    case_status: str = "active"
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    plaintiff_firm: Optional[str] = None
    defendant_firm: Optional[str] = None
    justice: Optional[str] = None
    part: Optional[str] = None
    notes: Optional[str] = None
    priority: str = "normal"
    court_system: str = "ny_webcivil"
    search_params: Optional[str] = None


# ─── Case Events ───
class CaseEventOut(BaseModel):
    id: int
    case_id: int
    event_type: str
    event_date: Optional[str] = None
    description: Optional[str] = None
    source: str = "manual"
    created_at: str


# ─── Appearances ───
class AppearanceCreate(BaseModel):
    appearance_date: date
    appearance_time: Optional[str] = None
    appearance_type: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class AppearanceUpdate(BaseModel):
    appearance_date: Optional[date] = None
    appearance_time: Optional[str] = None
    appearance_type: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class AppearanceOut(BaseModel):
    id: int
    case_id: int
    appearance_date: str
    appearance_time: Optional[str] = None
    appearance_type: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    source: str = "manual"
    created_at: str
    updated_at: str


class DashboardAppearance(BaseModel):
    appearance_id: int
    case_id: int
    appearance_date: str
    appearance_time: Optional[str] = None
    appearance_type: Optional[str] = None
    location: Optional[str] = None
    court_type: str
    county: str
    index_number: str
    case_status: str
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    justice: Optional[str] = None
    part: Optional[str] = None
    priority: str = "normal"
    source: str = "manual"
    freshness: Optional[FreshnessInfo] = None


# ─── Court Configs ───
class CourtConfigOut(BaseModel):
    id: int
    state: str
    court_system: str
    display_name: str
    base_url: Optional[str] = None
    adapter_class: str
    enabled: bool


# ─── Notifications ───
class NotificationSettingsUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    reminder_days: Optional[int] = None
    case_updates_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = None  # 'off', 'daily', 'weekly'
    digest_time: Optional[str] = None  # HH:MM format


class NotificationSettingsOut(BaseModel):
    id: int
    user_id: int
    email_enabled: bool
    push_enabled: bool = True
    reminder_days: int
    case_updates_enabled: bool
    digest_frequency: str = "off"
    digest_time: str = "08:00"


class NotificationOut(BaseModel):
    id: int
    user_id: int
    case_id: Optional[int] = None
    appearance_id: Optional[int] = None
    type: str
    title: str
    message: str
    read: bool
    push_sent: bool = False
    created_at: str


class PushTokenRegister(BaseModel):
    token: str
    device_name: Optional[str] = None
    platform: Optional[str] = None


class PushTokenOut(BaseModel):
    id: int
    user_id: int
    token: str
    device_name: Optional[str] = None
    platform: Optional[str] = None
    active: bool
    created_at: str


class UnreadCountOut(BaseModel):
    count: int


class CaseNotificationPrefsUpdate(BaseModel):
    push_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    priority_override: Optional[str] = None


class CaseNotificationPrefsOut(BaseModel):
    case_id: int
    user_id: int
    push_enabled: bool = True
    email_enabled: bool = True
    priority_override: Optional[str] = None


# ─── Email Integration ───
class EmailSetupResponse(BaseModel):
    """Response from email setup endpoint."""
    inbound_email: str
    forwarding_verified: bool
    provider: Optional[str] = None
    already_setup: bool = False


class EmailConfigOut(BaseModel):
    """Email configuration for a user."""
    id: int
    user_id: int
    inbound_email: str
    forwarding_verified: bool
    provider: Optional[str] = None
    created_at: str


class EmailVerifyResponse(BaseModel):
    """Response from email verification endpoint."""
    verified: bool
    inbound_email: Optional[str] = None


class EmailSetupGuideStep(BaseModel):
    """A single step in the email setup guide."""
    step: int
    title: str
    description: str
    url: Optional[str] = None
    completed: bool = False


class EmailSetupGuide(BaseModel):
    """Complete email setup guide with instructions."""
    inbound_email: Optional[str] = None
    forwarding_verified: bool = False
    steps: list[EmailSetupGuideStep]
    gmail_instructions: str
    outlook_instructions: str
    privacy_note: str


class EmailWebhookResponse(BaseModel):
    """Response from email webhook processing."""
    status: str
    events_found: int = 0
    message: str = ""
    results: list[dict] = []


class EmailLogOut(BaseModel):
    """Email processing log entry."""
    id: int
    sender: Optional[str] = None
    subject: Optional[str] = None
    events_extracted: int = 0
    received_at: str


# ─── Case Discovery ───
class DiscoverySettingsUpdate(BaseModel):
    """Update discovery settings."""
    enabled: Optional[bool] = None
    attorney_name: Optional[str] = None
    attorney_reg_number: Optional[str] = None
    search_courts: Optional[str] = None  # comma-separated court system IDs
    search_county: Optional[str] = None


class DiscoverySettingsOut(BaseModel):
    """Discovery settings response."""
    id: int
    user_id: int
    enabled: bool
    attorney_name: Optional[str] = None
    attorney_reg_number: Optional[str] = None
    search_courts: str = "ny_webcivil,ny_webcrimin"
    search_county: Optional[str] = None
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None


class DiscoveredCaseOut(BaseModel):
    """A discovered case that the user can accept or dismiss."""
    id: int
    user_id: int
    index_number: str
    court_type: str
    county: Optional[str] = None
    court_system: Optional[str] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    case_status: Optional[str] = None
    last_action: Optional[str] = None
    last_action_date: Optional[str] = None
    source_adapter: Optional[str] = None
    status: str = "pending"
    notification_id: Optional[int] = None
    discovered_at: str
    resolved_at: Optional[str] = None


class DiscoveryAcceptResponse(BaseModel):
    """Response from accepting a discovered case."""
    status: str
    case_id: Optional[int] = None
    message: str


class DiscoveryDismissResponse(BaseModel):
    """Response from dismissing a discovered case."""
    status: str
    message: str


class DiscoveryRunResponse(BaseModel):
    """Response from manually triggering discovery."""
    users_checked: int = 0
    total_discoveries: int = 0
    errors: int = 0
