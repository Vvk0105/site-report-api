from decimal import Decimal

from pydantic import BaseModel


class PlanCreateRequest(BaseModel):

    name: str
    description: str | None = None
    price: Decimal
    currency: str = "AUD"
    billing_cycle: str
    report_limit: int
    trial_days: int = 0
    is_trial: bool = False


class PlanUpdateRequest(BaseModel):

    name: str
    description: str | None = None
    price: Decimal
    currency: str
    billing_cycle: str
    report_limit: int
    trial_days: int
    is_trial: bool
    is_active: bool


class PlanResponse(BaseModel):

    id: int
    name: str
    description: str | None
    price: Decimal
    currency: str
    billing_cycle: str
    report_limit: int
    trial_days: int
    is_trial: bool
    is_active: bool

    class Config:
        from_attributes = True