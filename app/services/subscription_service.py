from fastapi import HTTPException

from app.enums.subscription import PlanType
from app.enums.subscription import SubscriptionStatus
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.report_repository import ReportRepository

from app.repositories.user_repository import (
    UserRepository,
)

class SubscriptionService:

    def __init__(self, db):
        self.db = db
        self.subscription_repo = SubscriptionRepository(db)
        self.report_repo = ReportRepository(db)
        self.user_repo = UserRepository(db)

    async def get_subscription(
        self,
        user_id: int,
    ):

        subscription = await self.subscription_repo.get_by_user_id(
            user_id
        )

        if not subscription:
            raise HTTPException(
                status_code=404,
                detail="Subscription not found",
            )

        reports_used = await self.report_repo.completed_count(
            user_id
        )

        if subscription.report_limit == -1:
            reports_remaining = -1
        else:
            reports_remaining = max(
                0,
                subscription.report_limit - reports_used,
            )

        return {
            "plan_type": subscription.plan_type.value,
            "status": subscription.status.value,
            "report_limit": subscription.report_limit,
            "reports_used": reports_used,
            "reports_remaining": reports_remaining,
        }

    async def validate_can_create_report(
        self,
        user_id: int,
    ):

        subscription = await self.subscription_repo.get_by_user_id(
            user_id
        )

        if not subscription:
            raise HTTPException(
                status_code=404,
                detail="Subscription not found",
            )

        if subscription.status != SubscriptionStatus.ACTIVE:
            raise HTTPException(
                status_code=403,
                detail="Subscription expired",
            )

        if subscription.plan_type == PlanType.YEARLY:
            return

        reports_used = await self.report_repo.completed_count(
            user_id
        )

        if reports_used >= subscription.report_limit:
            raise HTTPException(
                status_code=403,
                detail="Trial report limit reached",
            )
        
    async def admin_list(self):

        subscriptions = await self.subscription_repo.list_all()

        data = []

        for subscription in subscriptions:

            user = await self.user_repo.get_by_id(
                subscription.user_id
            )

            data.append(
                {
                    "id": subscription.id,
                    "user_id": user.id,
                    "email": user.email,
                    "plan_type": subscription.plan_type.value,
                    "status": subscription.status.value,
                    "report_limit": subscription.report_limit,
                    "start_date": subscription.start_date,
                    "end_date": subscription.end_date,
                }
            )

        return data
    
    async def admin_update(
        self,
        user_id: int,
        plan_type: str,
        report_limit: int,
        status: str,
        end_date,
    ):

        subscription = await self.subscription_repo.get_by_user_id(
            user_id
        )

        if not subscription:

            raise HTTPException(
                status_code=404,
                detail="Subscription not found",
            )

        subscription.plan_type = PlanType(
            plan_type
        )

        subscription.status = SubscriptionStatus(
            status
        )

        subscription.report_limit = report_limit

        subscription.end_date = end_date

        self.subscription_repo.update(
            subscription
        )

        await self.db.commit()

        return {
            "id": subscription.id,
            "user_id": subscription.user_id,
            "email": (
                await self.user_repo.get_by_id(
                    user_id
                )
            ).email,
            "plan_type": subscription.plan_type.value,
            "status": subscription.status.value,
            "report_limit": subscription.report_limit,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
        }