from datetime import datetime

from sqlalchemy import func
from sqlalchemy import select

from app.enums.subscription import PlanType
from app.enums.subscription import SubscriptionStatus
from app.enums.report import ReportStatus

from app.models.user import User
from app.models.report import Report
from app.models.subscription import Subscription

class DashboardRepository:

    def __init__(self, db):
        self.db = db

    async def total_users(self):
        result = await self.db.execute(
            select(func.count(User.id))
        )

        return result.scalar_one()

    async def active_users(self):

        result = await self.db.execute(
            select(func.count(User.id)).where(
                User.is_active == True
            )
        )

        return result.scalar_one()

    async def trial_users(self):

        result = await self.db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.plan_type == PlanType.TRIAL,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )

        return result.scalar_one()

    async def paid_users(self):

        result = await self.db.execute(
            select(func.count(Subscription.id)).where(
                Subscription.plan_type == PlanType.YEARLY,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )

        return result.scalar_one()

    async def total_reports(self):

        result = await self.db.execute(
            select(func.count(Report.id)).where(
                Report.status == ReportStatus.COMPLETED,
            )
        )

        return result.scalar_one()

    async def reports_today(self):

        today = datetime.utcnow().date()

        result = await self.db.execute(
            select(func.count(Report.id)).where(
                func.date(Report.completed_at) == today,
                Report.status == ReportStatus.COMPLETED,
            )
        )

        return result.scalar_one()

    async def reports_this_month(self):

        now = datetime.utcnow()

        result = await self.db.execute(
            select(func.count(Report.id)).where(
                func.extract(
                    "month",
                    Report.completed_at,
                ) == now.month,
                func.extract(
                    "year",
                    Report.completed_at,
                ) == now.year,
                Report.status == ReportStatus.COMPLETED,
            )
        )

        return result.scalar_one()