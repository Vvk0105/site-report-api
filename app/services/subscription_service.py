from fastapi import HTTPException

from app.enums.subscription import SubscriptionStatus
from app.repositories.plan_repository import PlanRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.utils.pagination import paginate

UNLIMITED = -1


class SubscriptionService:

    def __init__(self, db):
        self.db = db
        self.subscription_repo = SubscriptionRepository(db)
        self.report_repo = ReportRepository(db)
        self.user_repo = UserRepository(db)

    async def get_subscription(self, user_id: int) -> dict:
        subscription = await self.subscription_repo.get_by_user_id(user_id)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        reports_used = await self.report_repo.count_for_user(user_id)
        limit = subscription.plan.report_limit

        return {
            "plan_type": subscription.plan.name,
            "status": subscription.status.value,
            "report_limit": limit,
            "reports_used": reports_used,
            "reports_remaining": -1 if limit == UNLIMITED else max(0, limit - reports_used),
        }

    async def validate_can_create_report(self, user_id: int) -> None:
        """
        Must be called inside the transaction that inserts the report. The subscription
        row lock is held until that commit, so concurrent starts are serialised.
        """
        subscription = await self.subscription_repo.get_by_user_id(user_id, lock=True)

        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        if subscription.status != SubscriptionStatus.ACTIVE:
            raise HTTPException(status_code=403, detail="Your subscription has expired. Renew it to create new reports.")

        limit = subscription.plan.report_limit
        if limit == UNLIMITED:
            return

        reports_used = await self.report_repo.count_for_user(user_id)

        if reports_used >= limit:
            raise HTTPException(status_code=403, detail="You have used all the reports included in your plan. Upgrade to create more reports.")

    # ─── admin ─────────────────────────────────────────────────────────────

    async def admin_list(
        self,
        page: int,
        page_size: int,
        status: SubscriptionStatus | None = None,
        search: str | None = None,
    ) -> dict:
        total, subscriptions = await self.subscription_repo.list_paginated(
            page,
            page_size,
            status=status,
            search=search,
        )

        results = [
            {
                "id": subscription.id,
                "user_id": subscription.user_id,
                "email": subscription.user.email,
                "plan_type": subscription.plan.name,
                "status": subscription.status.value,
                "report_limit": subscription.plan.report_limit,
                "start_date": subscription.start_date,
                "end_date": subscription.end_date,
            }
            for subscription in subscriptions
        ]

        return paginate(total=total, page=page, page_size=page_size, results=results)

    async def admin_update(
        self,
        user_id: int,
        plan_id: int,
        status: SubscriptionStatus,
        end_date,
    ) -> dict:
        subscription = await self.subscription_repo.get_by_user_id(user_id, lock=True)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        plan = await PlanRepository(self.db).get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=400, detail="Plan not found")

        subscription.plan_id = plan.id
        subscription.plan = plan
        subscription.status = status
        subscription.end_date = end_date
        self.subscription_repo.update(subscription)

        user = await self.user_repo.get_by_id(user_id)
        await self.db.commit()

        return {
            "id": subscription.id,
            "user_id": subscription.user_id,
            "email": user.email,
            "plan_type": plan.name,
            "status": subscription.status.value,
            "report_limit": plan.report_limit,
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
        }
