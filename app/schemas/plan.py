from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer

BillingCycle = Literal["monthly", "yearly", "weekly", "daily", "lifetime"]

# -1 means unlimited reports.
UNLIMITED_REPORTS = -1


class PlanCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(ge=0, le=1_000_000)
    currency: str = Field(default="AUD", pattern=r"^[A-Z]{3}$")
    billing_cycle: BillingCycle
    report_limit: int = Field(ge=UNLIMITED_REPORTS)
    trial_days: int = Field(default=0, ge=0, le=3650)
    is_trial: bool = False


class PlanUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    price: float = Field(ge=0, le=1_000_000)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    billing_cycle: BillingCycle
    report_limit: int = Field(ge=UNLIMITED_REPORTS)
    trial_days: int = Field(ge=0, le=3650)
    is_trial: bool
    is_active: bool


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: float
    currency: str
    billing_cycle: str
    report_limit: int
    trial_days: int
    is_trial: bool
    is_active: bool

    @field_serializer("price")
    def _round_price(self, value: float) -> float:
        return round(float(value), 2)
