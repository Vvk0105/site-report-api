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