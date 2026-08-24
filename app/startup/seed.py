from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.plan import Plan
from app.core.config import settings
from app.core.security import hash_password
from app.core.logger import logger
from datetime import datetime, timezone

async def seed_admin(db: AsyncSession):

    result = await db.execute(
        select(User).where(User.is_admin == True)
    )

    admin = result.scalar_one_or_none()

    if admin:
        print("✅ Admin already exists")
        return

    admin = User(
        email=settings.ADMIN_EMAIL,
        full_name="Super Admin",
        password_hash=hash_password(settings.ADMIN_PASSWORD),
        is_admin=True,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    
    db.add(admin)

    await db.commit()

    print("✅ Admin created")


TRIAL_PLAN_NAME = "Free Trial"

TRIAL_PLAN_REPORT_LIMIT = 3

TRIAL_PLAN_DAYS = 7


async def seed_plans(db: AsyncSession):

    result = await db.execute(
        select(Plan).where(Plan.is_trial == True).order_by(Plan.id)
    )

    trial_plan = result.scalars().first()

    if trial_plan:

        if trial_plan.is_active:
            print("✅ Trial plan already exists")
        else:
            logger.warning(
                "Trial plan '%s' (id=%s) is inactive - "
                "new users will be created without a subscription",
                trial_plan.name,
                trial_plan.id,
            )

        return

    trial_plan = Plan(
        name=TRIAL_PLAN_NAME,
        description="Free trial plan assigned to new users on signup",
        price=0,
        currency="AUD",
        billing_cycle="monthly",
        report_limit=TRIAL_PLAN_REPORT_LIMIT,
        trial_days=TRIAL_PLAN_DAYS,
        is_trial=True,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(trial_plan)

    await db.commit()

    print("✅ Trial plan created")
