from pydantic import BaseModel
from pydantic import ConfigDict


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plan_type: str
    status: str
    report_limit: int
    reports_used: int
    reports_remaining: int