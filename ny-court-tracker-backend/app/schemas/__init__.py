from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date, datetime


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
    created_at: str
    updated_at: str
    next_appearance: Optional[str] = None


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


# ─── Notifications ───
class NotificationSettingsUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    reminder_days: Optional[int] = None
    case_updates_enabled: Optional[bool] = None


class NotificationSettingsOut(BaseModel):
    id: int
    user_id: int
    email_enabled: bool
    reminder_days: int
    case_updates_enabled: bool


class NotificationOut(BaseModel):
    id: int
    user_id: int
    case_id: Optional[int] = None
    appearance_id: Optional[int] = None
    type: str
    title: str
    message: str
    read: bool
    created_at: str
