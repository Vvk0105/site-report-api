from sqlalchemy import select
from sqlalchemy.orm import selectinload

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
            select(Payment)
            .options(selectinload(Payment.plan))
            .where(
                Payment.stripe_session_id == session_id,
            )
        )

        return result.scalar_one_or_none()
    
    async def history(
        self,
        user_id: int,
    ):

        result = await self.db.execute(

            select(Payment)
            .options(
                selectinload(Payment.user),
                selectinload(Payment.plan),
            )
            .where(
                Payment.user_id == user_id,
            )

            .order_by(
                Payment.created_at.desc(),
            )
        )

        return result.scalars().all()
    
    async def admin_list(self):

        result = await self.db.execute(

            select(Payment)
            .options(
                selectinload(Payment.user),
                selectinload(Payment.plan),
            )
            .order_by(
                Payment.created_at.desc(),
            )
        )

        return result.scalars().all()
    

    async def get_by_subscription(
        self,
        stripe_subscription_id: str,
    ):

        result = await self.db.execute(
            select(Payment).where(
                Payment.stripe_subscription_id
                == stripe_subscription_id
            )
        )

        return result.scalar_one_or_none()