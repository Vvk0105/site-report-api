from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.enums.payment import PaymentStatus
from app.models.payment import Payment


class PaymentRepository:

    def __init__(self, db):
        self.db = db

    def create(self, payment: Payment) -> None:
        self.db.add(payment)

    async def get_by_session(self, session_id: str) -> Payment | None:
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.plan))
            .where(Payment.stripe_session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def history(self, user_id: int):
        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.plan))
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
        )
        return result.scalars().all()

    async def admin_list(self, page: int, page_size: int):
        total = await self.db.scalar(select(func.count(Payment.id)))

        result = await self.db.execute(
            select(Payment)
            .options(selectinload(Payment.user), selectinload(Payment.plan))
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return total, result.scalars().all()

    async def latest_by_subscription(self, stripe_subscription_id: str) -> Payment | None:
        # A subscription can have several payments (renewals), so take the newest.
        result = await self.db.execute(
            select(Payment)
            .where(Payment.stripe_subscription_id == stripe_subscription_id)
            .order_by(Payment.created_at.desc(), Payment.id.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def revenue_by_period(self, start_date, end_date, trunc_unit: str):
        """Revenue grouped in SQL by period and currency, so no rows are loaded into memory."""
        period = func.date_trunc(trunc_unit, Payment.created_at).label("period")
        result = await self.db.execute(
            select(period, Payment.currency, func.sum(Payment.amount))
            .where(
                Payment.status == PaymentStatus.PAID,
                Payment.created_at >= start_date,
                Payment.created_at <= end_date,
            )
            .group_by(period, Payment.currency)
            .order_by(period)
        )
        return result.all()
