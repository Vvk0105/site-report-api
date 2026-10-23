from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class CheckoutRequest(BaseModel):
    plan_id: int


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class AppleReceiptRequest(BaseModel):
    # Signed StoreKit 2 transaction (JWS) from the app.
    receipt_data: str = Field(min_length=1, max_length=16_384)


class PaymentHistoryItem(BaseModel):
    """What a customer may see about their own payments. No Stripe internals."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    amount: float
    currency: str
    status: str
    created_at: datetime

    @field_serializer("status")
    def _status(self, value) -> str:
        return value.value if hasattr(value, "value") else str(value)
