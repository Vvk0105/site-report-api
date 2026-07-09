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