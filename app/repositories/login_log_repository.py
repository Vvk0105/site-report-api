from app.models.login_log import LoginLog
from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import or_
from app.models.user import User

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
            .order_by(
                LoginLog.login_at.desc(),
            )
        )

        if search:

            query = query.where(
                User.email.ilike(
                    f"%{search}%"
                )
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