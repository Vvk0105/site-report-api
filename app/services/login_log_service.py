from app.repositories.login_log_repository import LoginLogRepository
from app.repositories.user_repository import UserRepository
from app.utils.pagination import paginate

class LoginLogService:

    def __init__(self, db):

        self.db = db

        self.log_repo = LoginLogRepository(db)

        self.user_repo = UserRepository(db)

    async def list_logs(
        self,
        page,
        page_size,
        search,
    ):

        total, rows = await self.log_repo.admin_logs(
            page,
            page_size,
            search,
        )

        results = []

        for log, email in rows:

            results.append(
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "email": email,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "login_at": log.login_at,
                }
            )

        return paginate(
            total=total,
            page=page,
            page_size=page_size,
            results=results,
        )