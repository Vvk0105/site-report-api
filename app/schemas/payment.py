from pydantic import BaseModel


class CheckoutRequest(BaseModel):

    plan_id: int


class CheckoutResponse(BaseModel):

    checkout_url: str

    session_id: str


class AppleReceiptRequest(BaseModel):

    receipt_data: str  # base64-encoded receipt string from Flutter StoreKit