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

    async def revenue_chart(self, interval: str, start_date, end_date):
        payments = await self.repo.revenue_data(start_date, end_date)
        
        from collections import defaultdict
        
        aggregated = defaultdict(float)
        
        for payment in payments:
            if not payment.created_at:
                continue
            
            if interval == "daily":
                key = payment.created_at.strftime("%Y-%m-%d")
            elif interval == "weekly":
                # ISO year and week number
                year, week, _ = payment.created_at.isocalendar()
                key = f"{year}-W{week:02d}"
            elif interval == "monthly":
                key = payment.created_at.strftime("%Y-%m")
            elif interval == "yearly":
                key = payment.created_at.strftime("%Y")
            else:
                key = payment.created_at.strftime("%Y-%m-%d")
                
            aggregated[key] += float(payment.amount)
            
        data = [{"date": k, "revenue": round(v, 2)} for k, v in aggregated.items()]
        
        # Sort chronologically
        data.sort(key=lambda x: x["date"])
        
        return {"data": data}