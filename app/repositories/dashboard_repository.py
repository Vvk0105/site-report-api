from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select

from app.enums.report import ReportStatus
from app.enums.subscription import SubscriptionStatus
from app.models.plan import Plan
from app.models.report import Report
from app.models.subscription import Subscription
from app.models.user import User


class DashboardRepository:

    def __init__(self, db):
        self.db = db

    async def _count(self, query) -> int:
        return await self.db.scalar(query) or 0

    async def total_users(self) -> int:
        return await self._count(select(func.count(User.id)))

    async def active_users(self) -> int:
        return await self._count(select(func.count(User.id)).where(User.is_active.is_(True)))

    async def trial_users(self) -> int:
        return await self._count(
            select(func.count(Subscription.id))
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Plan.is_trial.is_(True), Subscription.status == SubscriptionStatus.ACTIVE)
        )

    async def paid_users(self) -> int:
        return await self._count(
            select(func.count(Subscription.id))
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(Plan.is_trial.is_(False), Subscription.status == SubscriptionStatus.ACTIVE)
        )

    async def total_reports(self) -> int:
        return await self._count(
            select(func.count(Report.id)).where(Report.status == ReportStatus.COMPLETED)
        )

    async def _completed_between(self, start: datetime, end: datetime) -> int:
        return await self._count(
            select(func.count(Report.id)).where(
                Report.status == ReportStatus.COMPLETED,
                Report.completed_at >= start,
                Report.completed_at < end,
            )
        )

    async def reports_today(self) -> int:
        now = datetime.now(timezone.utc)
        start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
        return await self._completed_between(start, start + timedelta(days=1))

    async def reports_this_month(self) -> int:
        now = datetime.now(timezone.utc)
        start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        end = datetime(now.year + (now.month == 12), now.month % 12 + 1, 1, tzinfo=timezone.utc)
        return await self._completed_between(start, end)
