from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.otp import OTPCode


class OTPRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(
        self,
        email: str,
        purpose: str = "login",
        *,
        lock: bool = False,
    ) -> OTPCode | None:
        query = (
            select(OTPCode)
            .where(OTPCode.email == email, OTPCode.purpose == purpose)
            .order_by(OTPCode.id.desc())
            .limit(1)
        )
        if lock:
            # Serialises verification attempts so the attempt counter cannot be raced.
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalars().first()

    def create(self, otp: OTPCode) -> None:
        self.db.add(otp)

    async def delete(self, otp: OTPCode) -> None:
        await self.db.delete(otp)

    async def delete_by_email(self, email: str, purpose: str = "login") -> None:
        await self.db.execute(
            delete(OTPCode).where(OTPCode.email == email, OTPCode.purpose == purpose)
        )

    def increment_attempt(self, otp: OTPCode) -> None:
        otp.attempts += 1
        self.db.add(otp)
