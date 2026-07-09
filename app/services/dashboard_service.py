from app.repositories.dashboard_repository import DashboardRepository


class DashboardService:

    def __init__(self, db):

        self.repo = DashboardRepository(db)

    async def dashboard(self):

        return {
            "total_users": await self.repo.total_users(),
            "active_users": await self.repo.active_users(),
            "trial_users": await self.repo.trial_users(),
            "paid_users": await self.repo.paid_users(),
            "total_reports": await self.repo.total_reports(),
            "reports_today": await self.repo.reports_today(),
            "reports_this_month": await self.repo.reports_this_month(),
        }