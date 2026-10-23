from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.payment_repository import PaymentRepository

INTERVAL_UNITS = {
    "daily": "day",
    "weekly": "week",
    "monthly": "month",
    "yearly": "year",
}


def _period_label(period, interval: str) -> str:
    if interval == "daily":
        return period.strftime("%Y-%m-%d")
    if interval == "weekly":
        year, week, _ = period.isocalendar()
        return f"{year}-W{week:02d}"
    if interval == "monthly":
        return period.strftime("%Y-%m")
    return period.strftime("%Y")


class DashboardService:

    def __init__(self, db):
        self.repo = DashboardRepository(db)
        self.payments = PaymentRepository(db)

    async def dashboard(self) -> dict:
        # Sequential on purpose: one AsyncSession cannot run queries concurrently.
        return {
            "total_users": await self.repo.total_users(),
            "active_users": await self.repo.active_users(),
            "trial_users": await self.repo.trial_users(),
            "paid_users": await self.repo.paid_users(),
            "total_reports": await self.repo.total_reports(),
            "reports_today": await self.repo.reports_today(),
            "reports_this_month": await self.repo.reports_this_month(),
        }

    async def revenue_chart(self, interval: str, start_date, end_date) -> dict:
        rows = await self.payments.revenue_by_period(
            start_date,
            end_date,
            INTERVAL_UNITS[interval],
        )

        # Aggregate per (label, currency): amounts in different currencies are never summed together.
        totals: dict[tuple[str, str], float] = {}
        for period, currency, amount in rows:
            key = (_period_label(period, interval), currency)
            totals[key] = totals.get(key, 0.0) + float(amount)

        data = [
            {"date": label, "currency": currency, "revenue": round(amount, 2)}
            for (label, currency), amount in sorted(totals.items())
        ]

        return {
            "currencies": sorted({currency for _, currency in totals}),
            "data": data,
        }
