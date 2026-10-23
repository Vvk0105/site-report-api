import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app.core.constants import (
    OTP_EXPIRE_MINUTES,
    OTP_MAX_ATTEMPTS,
    OTP_RESEND_SECONDS,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.enums.subscription import SubscriptionStatus
from app.models.login_log import LoginLog
from app.models.otp import OTPCode
from app.models.subscription import Subscription
from app.models.user import User
from app.repositories.login_log_repository import LoginLogRepository
from app.repositories.otp_repository import OTPRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.utils.email import normalize_email

logger = logging.getLogger("site-report")


class OTPService:

    def __init__(self, db, email_service):
        self.db = db
        self.user_repo = UserRepository(db)
        self.otp_repo = OTPRepository(db)
        self.login_repo = LoginLogRepository(db)
        self.subscription_repo = SubscriptionRepository(db)
        self.plan_repo = PlanRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)
        self.email_service = email_service

    async def send_otp(self, email: str) -> dict:
        email = normalize_email(email)
        now = datetime.now(timezone.utc)

        existing = await self.otp_repo.get_by_email(email)

        if existing:
            created = existing.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)

            if (now - created).total_seconds() < OTP_RESEND_SECONDS:
                raise HTTPException(
                    status_code=429,
                    detail=f"Please wait {OTP_RESEND_SECONDS} seconds before requesting another OTP.",
                )

            await self.otp_repo.delete(existing)

        otp = f"{secrets.randbelow(900000) + 100000}"

        self.otp_repo.create(
            OTPCode(
                email=email,
                otp_hash=hash_password(otp),
                expires_at=now + timedelta(minutes=OTP_EXPIRE_MINUTES),
            )
        )

        try:
            await self.db.flush()
            await self.email_service.send_otp(email=email, otp=otp)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            logger.exception("Failed to send OTP email")
            raise HTTPException(status_code=502, detail="Could not send the OTP email. Please try again.")

        return {"message": "OTP sent successfully"}

    async def verify_otp(self, email: str, otp: str) -> dict:
        email = normalize_email(email)

        # Lock the row so parallel guesses cannot exceed OTP_MAX_ATTEMPTS.
        otp_row = await self.otp_repo.get_by_email(email, lock=True)

        if not otp_row:
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")

        now = datetime.now(timezone.utc)
        expires = otp_row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        if now > expires:
            await self.otp_repo.delete(otp_row)
            await self.db.commit()
            raise HTTPException(status_code=400, detail="OTP expired")

        if not verify_password(otp, otp_row.otp_hash):
            self.otp_repo.increment_attempt(otp_row)

            if otp_row.attempts >= OTP_MAX_ATTEMPTS:
                await self.otp_repo.delete(otp_row)

            await self.db.commit()
            raise HTTPException(status_code=400, detail="Invalid OTP")

        user = await self.user_repo.get_by_email(email)

        if user and not user.is_active:
            await self.otp_repo.delete(otp_row)
            await self.db.commit()
            raise HTTPException(status_code=403, detail="Account is deactivated")

        if not user:
            user = await self._create_user(email)

        self.login_repo.create(LoginLog(user_id=user.id))

        access_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "is_admin": user.is_admin,
            }
        )

        refresh_token = self.refresh_repo.issue(user.id)

        await self.otp_repo.delete(otp_row)
        await self.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def _create_user(self, email: str) -> User:
        user = User(email=email, is_active=True, is_admin=False)
        self.user_repo.create(user)
        await self.db.flush()

        trial_plan = await self.plan_repo.get_trial_plan()

        if trial_plan:
            self.subscription_repo.create(
                Subscription(
                    user_id=user.id,
                    plan_id=trial_plan.id,
                    status=SubscriptionStatus.ACTIVE,
                    start_date=datetime.now(timezone.utc),
                )
            )
        else:
            logger.warning(
                "No active trial plan configured - user %s created without a subscription",
                email,
            )

        return user
