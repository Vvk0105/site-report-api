from datetime import datetime

from sqlalchemy import func
from sqlalchemy import select

from app.enums.subscription import SubscriptionStatus
from app.enums.report import ReportStatus

from app.models.user import User
from app.models.plan import Plan
from app.models.report import Report
from app.models.subscription import Subscription
from app.models.payment import Payment
from app.enums.payment import PaymentStatus

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
            select(func.count(Subscription.id)).join(
                Plan, Subscription.plan_id == Plan.id
            ).where(
                Plan.is_trial == True,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )

        return result.scalar_one()

    async def paid_users(self):

        result = await self.db.execute(
            select(func.count(Subscription.id)).join(
                Plan, Subscription.plan_id == Plan.id
            ).where(
                Plan.is_trial == False,
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

    async def revenue_data(self, start_date: datetime, end_date: datetime):
        result = await self.db.execute(
            select(Payment).where(
                Payment.status == PaymentStatus.PAID,
                Payment.created_at >= start_date,
                Payment.created_at <= end_date,
            ).order_by(Payment.created_at.asc())
        )
        return result.scalars().all()