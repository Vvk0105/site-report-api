from app.repositories.user_repository import UserRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.plan_repository import PlanRepository

from app.models.user import User
from app.models.subscription import Subscription

from app.enums.subscription import (
    SubscriptionStatus,
)

from datetime import datetime, timezone

from fastapi import HTTPException

from app.utils.pagination import paginate

class AdminUserService:

    def __init__(self, db):

        self.db = db

        self.user_repo = UserRepository(db)

        self.subscription_repo = SubscriptionRepository(db)

        self.report_repo = ReportRepository(db)

        self.plan_repo = PlanRepository(db)

    async def list_users(
        self,
        page,
        page_size,
        search,
        plan=None,
        status=None,
        date_from=None,
        date_to=None,
        sort="created_at",
        order="desc",
    ):

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

        results = []

        for user, subscription, reports_used in rows:

            results.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "is_admin": user.is_admin,
                    "created_at": user.created_at,
                    "plan_type": (
                        subscription.plan.name
                        if subscription
                        else "-"
                    ),
                    "reports_used": reports_used,
                }
            )

        return paginate(
            total=total,
            page=page,
            page_size=page_size,
            results=results,
        )

    async def create_user(
        self,
        email,
        full_name,
    ):

        exists = await self.user_repo.get_by_email(
            email
        )

        if exists:
            raise HTTPException(
                status_code=400,
                detail="Email already exists",
            )

        user = User(
            email=email,
            full_name=full_name,
            is_active=True,
            is_admin=False,
        )

        self.user_repo.create(user)

        await self.db.flush()

        trial_plan = await self.plan_repo.get_trial_plan()

        subscription = Subscription(
            user_id=user.id,
            plan_id=trial_plan.id,
            status=SubscriptionStatus.ACTIVE,
            start_date=datetime.now(
                timezone.utc,
            ),
        )

        self.subscription_repo.create(
            subscription,
        )

        await self.db.commit()

        await self.db.refresh(user)

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "plan_type": subscription.plan.name,
            "reports_used": 0,
        }
    
    async def get_user(
        self,
        user_id: int,
    ):

        user = await self.user_repo.get_by_id(
            user_id
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        subscription = await self.subscription_repo.get_by_user_id(
            user.id
        )

        reports_used = await self.report_repo.completed_count(
            user.id
        )

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "plan_type": (
                subscription.plan.name
                if subscription
                else "-"
            ),
            "subscription_status": (
                subscription.status.value
                if subscription
                else "-"
            ),
            "report_limit": (
                subscription.plan.report_limit
                if subscription
                else 0
            ),
            "reports_used": reports_used,
        }
    
    async def update_user(
        self,
        user_id: int,
        full_name: str | None,
        is_active: bool,
        is_admin: bool,
    ):

        user = await self.user_repo.get_by_id(
            user_id
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        user.full_name = full_name
        user.is_active = is_active
        user.is_admin = is_admin

        self.user_repo.update(user)

        await self.db.commit()

        subscription = await self.subscription_repo.get_by_user_id(
            user.id
        )

        reports_used = await self.report_repo.completed_count(
            user.id
        )

        return {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
            "plan_type": (
                subscription.plan.name
                if subscription
                else "-"
            ),
            "reports_used": reports_used,
        }
    
    async def delete_user(
        self,
        user_id: int,
    ):

        user = await self.user_repo.get_by_id(
            user_id
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        if user.is_admin:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete admin",
            )

        await self.user_repo.delete(
            user,
        )

        await self.db.commit()

        return {
            "message": "User deleted successfully"
        }