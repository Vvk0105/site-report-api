from datetime import datetime

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr
from datetime import datetime


class DashboardResponse(BaseModel):
    total_users: int

    active_users: int

    trial_users: int

    paid_users: int

    total_reports: int

    reports_today: int

    reports_this_month: int

class AdminUserResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    email: EmailStr

    full_name: str | None

    is_active: bool

    is_admin: bool

    created_at: datetime

    plan_type: str

    reports_used: int


class AdminUserListResponse(BaseModel):

    total: int

    page: int

    page_size: int

    results: list[AdminUserResponse]


class CreateUserRequest(BaseModel):

    email: EmailStr

    full_name: str | None = None


class UpdateUserRequest(BaseModel):

    full_name: str | None = None

    is_active: bool

class AdminUserDetailResponse(BaseModel):

    id: int

    email: EmailStr

    full_name: str | None

    is_active: bool

    is_admin: bool

    created_at: datetime

    plan_type: str

    subscription_status: str

    report_limit: int

    reports_used: int

class UpdateUserRequest(BaseModel):

    full_name: str | None = None

    is_active: bool

    is_admin: bool

class UpdateSubscriptionRequest(BaseModel):

    plan_type: str

    report_limit: int

    status: str

    end_date: datetime | None = None

class AdminSubscriptionResponse(BaseModel):

    id: int

    user_id: int

    email: EmailStr

    plan_type: str

    status: str

    report_limit: int

    start_date: datetime

    end_date: datetime | None

class AdminReportResponse(BaseModel):

    id: int

    report_number: str

    user_id: int

    inspector_email: EmailStr

    status: str

    email_sent: bool

    device_id: str | None

    app_version: str | None

    created_at: datetime

    completed_at: datetime | None


class AdminReportListResponse(BaseModel):

    total: int

    page: int

    page_size: int

    results: list[AdminReportResponse]

class LoginLogResponse(BaseModel):

    id: int

    user_id: int

    email: EmailStr

    ip_address: str | None

    user_agent: str | None

    login_at: datetime


class LoginLogListResponse(BaseModel):

    total: int

    page: int

    page_size: int

    results: list[LoginLogResponse]