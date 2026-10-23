from sqlalchemy import and_, func, select

from app.models.login_log import LoginLog
from app.models.user import User
from app.utils.query import apply_order, escape_like, safe_sort_column

LOGIN_LOG_SORT_COLUMNS = {"id", "login_at", "user_id"}


class LoginLogRepository:

    def __init__(self, db):
        self.db = db

    def create(self, log: LoginLog) -> None:
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
        query = select(LoginLog, User.email.label("email")).join(
            User, User.id == LoginLog.user_id
        )

        filters = []

        if search:
            filters.append(User.email.ilike(f"%{escape_like(search)}%", escape="\\"))

        if date_from:
            filters.append(LoginLog.login_at >= date_from)

        if date_to:
            filters.append(LoginLog.login_at <= date_to)

        if filters:
            query = query.where(and_(*filters))

        sort_column = safe_sort_column(LoginLog, sort, LOGIN_LOG_SORT_COLUMNS, "login_at")
        query = apply_order(query, sort_column, order)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))

        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )

        return total, result.all()
