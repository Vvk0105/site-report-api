from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from sqlalchemy import func
from sqlalchemy import or_

from app.models.subscription import Subscription
from app.models.report import Report
from app.models.plan import Plan
from app.enums.report import ReportStatus
from sqlalchemy import and_, asc, desc
from sqlalchemy.orm import selectinload

class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str):

        result = await self.db.execute(
            select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()

    def create(
        self,
        user: User,
    ):
        self.db.add(user)


    async def get_by_id(
        self,
        user_id: int,
    ):

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )

        return result.scalar_one_or_none()
    
    async def exists_by_email(self, email: str) -> bool:

        result = await self.db.execute(
            select(User.id).where(User.email == email)
        )

        return result.scalar_one_or_none() is not None
    
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

        report_count = (
            select(
                Report.user_id,
                func.count(
                    Report.id
                ).label(
                    "reports_used"
                ),
            )
            .where(
                Report.status == ReportStatus.COMPLETED,
            )
            .group_by(
                Report.user_id,
            )
            .subquery()
        )

        query = (
            select(
                User,
                Subscription,
                func.coalesce(
                    report_count.c.reports_used,
                    0,
                ).label(
                    "reports_used",
                ),
            )
            .outerjoin(
                Subscription,
                Subscription.user_id == User.id,
            )
            .outerjoin(
                report_count,
                report_count.c.user_id == User.id,
            )
            .outerjoin(
                Plan,
                Plan.id == Subscription.plan_id,
            )
            .options(
                selectinload(Subscription.plan)
            )
        )

        filters = []

        if search:

            filters.append(
                or_(
                    User.email.ilike(
                        f"%{search}%"
                    ),
                    User.full_name.ilike(
                        f"%{search}%"
                    ),
                )
            )

        if plan:

            filters.append(
                Plan.name == plan
            )

        if status is not None:

            filters.append(
                User.is_active == status
            )

        if date_from:

            filters.append(
                User.created_at >= date_from
            )

        if date_to:

            filters.append(
                User.created_at <= date_to
            )

        if filters:

            query = query.where(
                and_(
                    *filters,
                )
            )

        sort_column = getattr(
            User,
            sort,
            User.created_at,
        )

        if order == "asc":

            query = query.order_by(
                asc(sort_column),
            )

        else:

            query = query.order_by(
                desc(sort_column),
            )

        total = await self.db.scalar(
            select(func.count()).select_from(
                query.subquery()
            )
        )

        result = await self.db.execute(
            query.offset(
                (page - 1) * page_size
            ).limit(page_size)
        )

        return total, result.all()
    
    def create(
        self,
        user: User,
    ):

        self.db.add(user)

    async def get(
        self,
        user_id: int,
    ):

        result = await self.db.execute(
            select(User).where(
                User.id == user_id
            )
        )

        return result.scalar_one_or_none()
    
    async def delete(
        self,
        user: User,
    ):

        user.is_active = False
        self.db.add(user)

    def update(
        self,
        user: User,
    ):

        self.db.add(user)