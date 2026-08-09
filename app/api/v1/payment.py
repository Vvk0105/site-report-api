from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

from app.dependencies import get_current_user

from app.schemas.payment import (
    CheckoutRequest,
    CheckoutResponse,
    AppleReceiptRequest,
)

from app.services.payment_service import PaymentService


router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


@router.post(
    "/checkout",
    response_model=CheckoutResponse,
)
async def checkout(
    request: CheckoutRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    return await PaymentService(
        db,
    ).checkout(
        plan_id=request.plan_id,
        user=current_user,
    )

@router.post(
    "/webhook",
)
async def webhook(
    request: Request,
    stripe_signature: str = Header(
        alias="Stripe-Signature",
    ),
    db: AsyncSession = Depends(get_db),
):

    payload = await request.body()

    return await PaymentService(
        db,
    ).webhook(
        payload,
        stripe_signature,
    )

@router.get(
    "/history",
)
async def history(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    return await PaymentService(
        db,
    ).history(
        current_user,
    )

@router.get(
    "/{session_id}",
)
async def verify_payment(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):

    return await PaymentService(
        db,
    ).verify(
        session_id,
    )

@router.get(
    "/customer-portal",
)
async def customer_portal(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    return await PaymentService(
        db,
    ).customer_portal(
        current_user,
    )


@router.post("/apple/verify-receipt")
async def apple_verify_receipt(
    request: AppleReceiptRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Called by the Flutter app (iOS only) after a successful StoreKit purchase.
    Verifies the receipt with Apple and upgrades the user's subscription.
    Requires: Authorization Bearer token in header.
    """
    return await PaymentService(db).verify_apple_receipt(
        receipt_data=request.receipt_data,
        user=current_user,
    )


@router.post("/apple/webhook")
async def apple_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Apple server-to-server notifications endpoint.
    URL configured in App Store Connect → App Information → Server Notifications.
    No auth header needed — Apple calls this directly.
    """
    payload = await request.json()
    return await PaymentService(db).handle_apple_webhook(payload)