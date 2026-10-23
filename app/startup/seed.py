from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logger import logger
from app.core.security import hash_password
from app.models.plan import Plan
from app.models.user import User
from app.utils.email import normalize_email

TRIAL_PLAN_NAME = "Free Trial"
TRIAL_PLAN_REPORT_LIMIT = 3
TRIAL_PLAN_DAYS = 7


async def seed_admin(db: AsyncSession) -> None:
    """Make sure the configured admin account exists. Idempotent and safe to run on every start."""
    email = normalize_email(settings.ADMIN_EMAIL)

    result = await db.execute(select(User).where(User.email == email))
    admin = result.scalars().first()

    if admin:
        changed = False
        if not admin.is_admin:
            admin.is_admin = True
            changed = True
        if not admin.is_active:
            admin.is_active = True
            changed = True
        if not admin.password_hash:
            admin.password_hash = hash_password(settings.ADMIN_PASSWORD)
            changed = True
        if changed:
            await db.commit()
            logger.info("Admin account %s updated", email)
        return

    db.add(
        User(
            email=email,
            full_name="Super Admin",
            password_hash=hash_password(settings.ADMIN_PASSWORD),
            is_admin=True,
            is_active=True,
        )
    )
    await db.commit()
    logger.info("Admin account %s created", email)


async def seed_plans(db: AsyncSession) -> None:
    result = await db.execute(
        select(Plan).where(Plan.is_trial.is_(True)).order_by(Plan.id).limit(1)
    )
    trial_plan = result.scalars().first()

    if trial_plan:
        if not trial_plan.is_active:
            logger.warning(
                "Trial plan '%s' (id=%s) is inactive - new users will be created without a subscription",
                trial_plan.name,
                trial_plan.id,
            )
        return

    now = datetime.now(timezone.utc)
    db.add(
        Plan(
            name=TRIAL_PLAN_NAME,
            description="Free trial plan assigned to new users on signup",
            price=0,
            currency="AUD",
            billing_cycle="monthly",
            report_limit=TRIAL_PLAN_REPORT_LIMIT,
            trial_days=TRIAL_PLAN_DAYS,
            is_trial=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    await db.commit()
    logger.info("Trial plan created")
