import asyncio
import logging

import stripe
from sqlalchemy import delete, func, select, update

from app.models.login_log import LoginLog
from app.models.otp import OTPCode
from app.models.payment import Payment
from app.models.refresh_token import RefreshToken
from app.models.report import Report
from app.models.subscription import Subscription
from app.models.user import User

logger = logging.getLogger("site-report")


async def revoke_sessions(db, user_id: int) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )


async def has_payments(db, user_id: int) -> bool:
    count = await db.scalar(
        select(func.count(Payment.id)).where(Payment.user_id == user_id)
    )
    return bool(count)


async def purge_personal_data(db, user: User) -> None:
    """
    Remove everything tied to the person and anonymise the account row.
    Payment rows are kept (financial records have retention requirements), but
    they no longer point at any identifiable details.
    """
    await revoke_sessions(db, user.id)

    await db.execute(delete(OTPCode).where(OTPCode.email == user.email))
    await db.execute(delete(LoginLog).where(LoginLog.user_id == user.id))
    await db.execute(delete(Report).where(Report.user_id == user.id))
    await db.execute(delete(Subscription).where(Subscription.user_id == user.id))

    user.email = f"deleted-{user.id}@deleted.invalid"
    user.full_name = None
    user.password_hash = None
    user.is_active = False
    user.is_admin = False
    user.stripe_customer_id = None

    db.add(user)


async def delete_stripe_customer(customer_id: str | None) -> None:
    """Best effort: the local data is already gone even if Stripe is unreachable."""
    if not customer_id:
        return
    try:
        await asyncio.to_thread(stripe.Customer.delete, customer_id)
    except Exception:
        logger.exception("Could not delete Stripe customer %s", customer_id)
