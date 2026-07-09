from enum import Enum


class PlanType(str, Enum):
    TRIAL = "trial"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"