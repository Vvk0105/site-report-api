from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.plan import Plan
from app.models.report import Report
from app.models.subscription import Subscription
from app.models.user import User
from app.utils.query import apply_order, escape_like, safe_sort_column

USER_SORT_COLUMNS = {"id", "email", "full_name", "is_active", "is_admin", "created_at"}


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    def create(self, user: User) -> None:
        self.db.add(user)

    def update(self, user: User) -> None:
        self.db.add(user)

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_stripe_customer_id(self, customer_id: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        return result.scalar_one_or_none()

    async def admin_users(
        self,
        page: int,
        page_size: int,
        search: str | None,
        plan: str | None = None,
        status: bool | None = None,
        date_from=None,
        date_to=None,
        sort: str = "created_at",
        order: str = "desc",
    ):
        # Every report counts against the quota (see SubscriptionService),
        # so the admin view uses the same definition as the app.
        report_count = (
            select(
                Report.user_id,
                func.count(Report.id).label("reports_used"),
            )
            .group_by(Report.user_id)
            .subquery()
        )

        query = (
            select(
                User,
                Subscription,
                func.coalesce(report_count.c.reports_used, 0).label("reports_used"),
            )
            .outerjoin(Subscription, Subscription.user_id == User.id)
            .outerjoin(Plan, Plan.id == Subscription.plan_id)
            .outerjoin(report_count, report_count.c.user_id == User.id)
            .options(selectinload(Subscription.plan))
        )

        filters = []

        if search:
            pattern = f"%{escape_like(search)}%"
            filters.append(
                or_(
                    User.email.ilike(pattern, escape="\\"),
                    User.full_name.ilike(pattern, escape="\\"),
                )
            )

        if plan:
            filters.append(Plan.name == plan)

        if status is not None:
            filters.append(User.is_active == status)

        if date_from:
            filters.append(User.created_at >= date_from)

        if date_to:
            filters.append(User.created_at <= date_to)

        if filters:
            query = query.where(and_(*filters))

        sort_column = safe_sort_column(User, sort, USER_SORT_COLUMNS, "created_at")
        query = apply_order(query, sort_column, order)

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )

        return total, result.all()
