from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete

from app.enums.subscription import SubscriptionStatus
from app.models.login_log import LoginLog
from app.models.otp import OTPCode
from app.models.refresh_token import RefreshToken
from app.models.report import Report
from app.models.subscription import Subscription
from app.models.user import User
from app.repositories.plan_repository import PlanRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.account_service import has_payments, revoke_sessions
from app.utils.email import normalize_email
from app.utils.pagination import paginate


class AdminUserService:

    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.subscription_repo = SubscriptionRepository(db)
        self.report_repo = ReportRepository(db)
        self.plan_repo = PlanRepository(db)

    async def list_users(self, page, page_size, search, plan=None, status=None,
                         date_from=None, date_to=None, sort="created_at", order="desc"):
        total, rows = await self.user_repo.admin_users(
            page=page,
            page_size=page_size,
            search=search,
            plan=plan,
            status=status,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
            order=order,
        )

        results = [
            {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "created_at": user.created_at,
                "plan_type": subscription.plan.name if subscription and subscription.plan else "-",
                "reports_used": reports_used,
            }
            for user, subscription, reports_used in rows
        ]

        return paginate(total=total, page=page, page_size=page_size, results=results)

    async def create_user(self, email: str, full_name: str | None):
        email = normalize_email(email)

        if await self.user_repo.get_by_email(email):
            raise HTTPException(status_code=400, detail="Email already exists")

        user = User(email=email, full_name=full_name, is_active=True, is_admin=False)
        self.user_repo.create(user)
        await self.db.flush()

        plan = await self.plan_repo.get_trial_plan()
        subscription = None
        if plan:
            subscription = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                start_date=datetime.now(timezone.utc),
            )
            self.subscription_repo.create(subscription)
            subscription.plan = plan

        await self.db.commit()
        await self.db.refresh(user)

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "plan_type": plan.name if plan else "-",
            "reports_used": 0,
        }

    async def get_user(self, user_id: int):
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        subscription = await self.subscription_repo.get_by_user_id(user.id)
        reports_used = await self.report_repo.count_for_user(user.id)

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "plan_id": subscription.plan_id if subscription else None,
            "plan_type": subscription.plan.name if subscription else "-",
            "subscription_status": subscription.status.value if subscription else "-",
            "subscription_end_date": subscription.end_date if subscription else None,
            "report_limit": subscription.plan.report_limit if subscription else 0,
            "reports_used": reports_used,
        }

    async def update_user(
        self,
        *,
        acting_admin_id: int,
        user_id: int,
        full_name_provided: bool,
        full_name: str | None,
        is_active: bool,
        is_admin: bool,
    ):
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Stops an admin from locking themselves (or the last admin) out.
        if user.id == acting_admin_id and (not is_admin or not is_active):
            raise HTTPException(status_code=400, detail="You cannot remove your own admin access or deactivate yourself")

        if full_name_provided:
            user.full_name = full_name

        if user.is_active and not is_active:
            await revoke_sessions(self.db, user.id)

        user.is_active = is_active
        user.is_admin = is_admin
        self.user_repo.update(user)
        await self.db.commit()

        return await self.get_user(user.id)

    async def delete_user(self, *, acting_admin_id: int, user_id: int, hard: bool = False):
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.is_admin:
            raise HTTPException(status_code=400, detail="Cannot delete an admin account")

        if user.id == acting_admin_id:
            raise HTTPException(status_code=400, detail="You cannot delete your own account")

        if not hard:
            # Soft delete: keeps data, blocks access immediately.
            await revoke_sessions(self.db, user.id)
            user.is_active = False
            self.user_repo.update(user)
            await self.db.commit()
            return {"message": "User deactivated"}

        if await has_payments(self.db, user.id):
            # Payment records are financial data; they must not be erased by a click.
            raise HTTPException(
                status_code=409,
                detail="This user has payment history and cannot be permanently deleted. Deactivate the account instead.",
            )

        await self.db.execute(delete(LoginLog).where(LoginLog.user_id == user.id))
        await self.db.execute(delete(OTPCode).where(OTPCode.email == user.email))
        await self.db.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
        await self.db.execute(delete(Report).where(Report.user_id == user.id))
        await self.db.execute(delete(Subscription).where(Subscription.user_id == user.id))
        await self.db.delete(user)
        await self.db.commit()

        return {"message": "User permanently deleted"}
