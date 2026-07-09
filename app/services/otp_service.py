import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.core.constants import (
    OTP_EXPIRE_MINUTES,
    OTP_RESEND_SECONDS,
)
from app.core.security import hash_password
from app.models.otp import OTPCode
from app.core.constants import OTP_MAX_ATTEMPTS
from app.core.security import (
    verify_password,
    create_access_token,
)

from app.models.login_log import LoginLog
from app.models.user import User

from datetime import datetime, timezone

from app.enums.subscription import (
    PlanType,
    SubscriptionStatus,
)
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.login_log_repository import LoginLogRepository
from app.repositories.otp_repository import OTPRepository
from app.models.subscription import Subscription

class OTPService:

    def __init__(
        self,
        db,
        email_service,
    ):

        self.db = db
        self.user_repo = UserRepository(db)
        self.otp_repo = OTPRepository(db)
        self.login_repo = LoginLogRepository(db)
        self.subscription_repo = SubscriptionRepository(db)
        self.email_service = email_service

    async def send_otp(self, email: str):

        existing = await self.otp_repo.get_by_email(email)

        now = datetime.now(timezone.utc)

        if existing:

            created = existing.created_at

            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            seconds = (now - created).total_seconds()

            if seconds < OTP_RESEND_SECONDS:
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {OTP_RESEND_SECONDS} seconds before requesting another OTP.",
                )

            await self.otp_repo.delete(existing)

        otp = str(
            secrets.randbelow(900000) + 100000
        )

        otp_model = OTPCode(
            email=email,
            otp_hash=hash_password(otp),
            expires_at=now + timedelta(
                minutes=OTP_EXPIRE_MINUTES
            ),
        )

        try:
            self.otp_repo.create(otp_model)

            await self.db.flush()

            await self.email_service.send_otp(
                email=email,
                otp=otp,
            )

            await self.db.commit()

        except Exception:
            await self.db.rollback()
            raise

        return {
            "message": "OTP sent successfully"
        }
    
    async def verify_otp(
        self,
        email: str,
        otp: str,
    ):

        otp_row = await self.otp_repo.get_by_email(email)

        if not otp_row:
            raise HTTPException(
                status_code=404,
                detail="OTP not found",
            )

        now = datetime.now(timezone.utc)

        expires = otp_row.expires_at

        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if now > expires:

            await self.otp_repo.delete(otp_row)

            await self.db.commit()

            raise HTTPException(
                status_code=400,
                detail="OTP expired",
            )

        if not verify_password(
            otp,
            otp_row.otp_hash,
        ):

            self.otp_repo.increment_attempt(
                otp_row
            )

            if otp_row.attempts >= OTP_MAX_ATTEMPTS:

                await self.otp_repo.delete(
                    otp_row
                )

            await self.db.commit()

            raise HTTPException(
                status_code=400,
                detail="Invalid OTP",
            )

        user = await self.user_repo.get_by_email(email)

        if not user:

            user = User(
                email=email,
                is_active=True,
                is_admin=False,
            )

            self.user_repo.create(user)

            await self.db.flush()

            subscription = Subscription(
                user_id=user.id,
                plan_type=PlanType.TRIAL,
                status=SubscriptionStatus.ACTIVE,
                report_limit=5,
                start_date=datetime.now(timezone.utc),
            )

            self.subscription_repo.create(subscription)

        self.login_repo.create(
            LoginLog(
                user_id=user.id,
            )
        )

        token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "is_admin": user.is_admin,
            }
        )

        await self.otp_repo.delete(otp_row)

        await self.db.commit()

        return {
            "access_token": token,
            "token_type": "bearer",
        }