from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.dependencies import get_current_user
from app.schemas.payment import AppleReceiptRequest, CheckoutRequest, CheckoutResponse, PaymentHistoryItem
from app.services.payment_service import PaymentService

router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


@router.post("/checkout", response_model=CheckoutResponse)
async def checkout(
    request: CheckoutRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await PaymentService(db).checkout(plan_id=request.plan_id, user=current_user)


@router.post("/webhook")
async def webhook(
    request: Request,
    stripe_signature: str = Header(alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    return await PaymentService(db).webhook(payload, stripe_signature)


@router.get("/history", response_model=list[PaymentHistoryItem])
async def history(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await PaymentService(db).history(current_user)


# Must be declared before the `/{session_id}` route, otherwise "customer-portal"
# is captured as a session id and this endpoint is unreachable.
@router.get("/customer-portal")
async def customer_portal(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await PaymentService(db).customer_portal(current_user)


@router.get("/{session_id}")
async def verify_payment(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Public: used by the post-checkout page. Returns only the paid status."""
    return await PaymentService(db).verify(session_id)


@router.post("/apple/verify-receipt")
async def apple_verify_receipt(
    request: AppleReceiptRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Called by the mobile app after a StoreKit purchase. The token is verified against Apple's chain."""
    return await PaymentService(db).verify_apple_receipt(
        receipt_data=request.receipt_data,
        user=current_user,
    )


@router.post("/apple/webhook")
async def apple_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """App Store Server Notifications. Apple calls this directly; every notification is signature-checked."""
    try:
        payload = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    return await PaymentService(db).handle_apple_webhook(payload)
