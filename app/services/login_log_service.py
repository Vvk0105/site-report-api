from app.repositories.login_log_repository import LoginLogRepository
from app.repositories.user_repository import UserRepository


class LoginLogService:

    def __init__(self, db):

        self.db = db

        self.log_repo = LoginLogRepository(db)

        self.user_repo = UserRepository(db)

    async def list_logs(
        self,
        page,
        page_size,
    ):

        total, logs = await self.log_repo.admin_logs(
            page,
            page_size,
        )

        results = []

        for log in logs:

            user = await self.user_repo.get_by_id(
                log.user_id
            )

            results.append(
                {
                    "id": log.id,
                    "user_id": user.id,
                    "email": user.email,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "login_at": log.login_at,
                }
            )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": results,
        }