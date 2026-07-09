from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.config import settings
from app.core.security import hash_password


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
    )

    db.add(admin)

    await db.commit()

    print("✅ Admin created")