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
    ) -> OTPCode | None:

        result = await self.db.execute(
            select(OTPCode).where(
                OTPCode.email == email,
                OTPCode.purpose == purpose,
            )
        )

        return result.scalar_one_or_none()

    def create(
        self,
        otp: OTPCode,
    ):
        self.db.add(otp)


    def update(
        self,
        otp: OTPCode,
    ):
        self.db.add(otp)

        self.db.add(otp)

    async def delete(
        self,
        otp: OTPCode,
    ):

        await self.db.delete(otp)

    async def delete_by_email(
        self,
        email: str,
        purpose: str = "login",
    ):

        await self.db.execute(
            delete(OTPCode).where(
                OTPCode.email == email,
                OTPCode.purpose == purpose,
            )
        )

    def increment_attempt(
        self,
        otp: OTPCode,
    ):
        otp.attempts += 1
        self.db.add(otp)