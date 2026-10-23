from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.enums.subscription import SubscriptionStatus


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


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


class AdminUserListResponse(PageMeta):
    results: list[AdminUserResponse]


class AdminUserDetailResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime
    plan_id: int | None
    plan_type: str
    subscription_status: str
    subscription_end_date: datetime | None = None
    report_limit: int
    reports_used: int


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)


class UpdateUserRequest(BaseModel):
    # Omitted means "leave unchanged"; an explicit null clears the name.
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool
    is_admin: bool


class UpdateSubscriptionRequest(BaseModel):
    plan_id: int
    status: SubscriptionStatus
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


class AdminSubscriptionListResponse(PageMeta):
    results: list[AdminSubscriptionResponse]


class AdminPaymentResponse(BaseModel):
    id: int
    user_id: int
    user_email: str
    plan: str
    amount: float
    currency: str
    status: str
    stripe_session_id: str
    created_at: datetime


class AdminPaymentListResponse(PageMeta):
    results: list[AdminPaymentResponse]


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


class AdminReportListResponse(PageMeta):
    results: list[AdminReportResponse]


class LoginLogResponse(BaseModel):
    id: int
    user_id: int
    email: EmailStr
    ip_address: str | None
    user_agent: str | None
    login_at: datetime


class LoginLogListResponse(PageMeta):
    results: list[LoginLogResponse]


class RevenueChartPoint(BaseModel):
    date: str
    currency: str
    revenue: float


class RevenueChartResponse(BaseModel):
    # Revenue is never summed across currencies; the client picks one.
    currencies: list[str]
    data: list[RevenueChartPoint]
