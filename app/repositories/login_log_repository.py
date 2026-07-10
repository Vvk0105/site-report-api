from app.models.login_log import LoginLog
from sqlalchemy import func
from sqlalchemy import select

class LoginLogRepository:

    def __init__(self, db):
        self.db = db

    def create(self, log: LoginLog):
        self.db.add(log)

    async def admin_logs(
        self,
        page: int,
        page_size: int,
    ):

        query = (
            select(LoginLog)
            .order_by(
                LoginLog.login_at.desc()
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

        return total, result.scalars().all()