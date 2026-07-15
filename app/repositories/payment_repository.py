from sqlalchemy import select

from app.models.payment import Payment


class PaymentRepository:

    def __init__(
        self,
        db,
    ):
        self.db = db

    def create(
        self,
        payment,
    ):
        self.db.add(payment)

    async def get_by_session(
        self,
        session_id: str,
    ):

        result = await self.db.execute(
            select(Payment).where(
                Payment.stripe_session_id == session_id,
            )
        )

        return result.scalar_one_or_none()