from app.models.login_log import LoginLog
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import or_
from app.models.user import User
from sqlalchemy import and_, asc, desc

class LoginLogRepository:

    def __init__(self, db):
        self.db = db

    def create(self, log: LoginLog):
        self.db.add(log)

    async def admin_logs(
        self,
        page: int,
        page_size: int,
        search: str | None,
        date_from=None,
        date_to=None,
        sort: str = "login_at",
        order: str = "desc",
    ):

        query = (
            select(
                LoginLog,
                User.email.label("email"),
            )
            .join(
                User,
                User.id == LoginLog.user_id,
            )
        )

        filters = []

        if search:

            filters.append(
                User.email.ilike(
                    f"%{search}%"
                )
            )

        if date_from:

            filters.append(
                LoginLog.login_at >= date_from
            )

        if date_to:

            filters.append(
                LoginLog.login_at <= date_to
            )

        if filters:

            query = query.where(
                and_(*filters)
            )

        sort_column = getattr(
            LoginLog,
            sort,
            LoginLog.login_at,
        )

        query = query.order_by(
            asc(sort_column)
            if order == "asc"
            else desc(sort_column)
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