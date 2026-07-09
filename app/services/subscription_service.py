from fastapi import HTTPException

from app.enums.subscription import PlanType
from app.enums.subscription import SubscriptionStatus
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.report_repository import ReportRepository


class SubscriptionService:

    def __init__(self, db):

        self.subscription_repo = SubscriptionRepository(db)
        self.report_repo = ReportRepository(db)

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