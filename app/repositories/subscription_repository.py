from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.subscription import Subscription


class SubscriptionRepository:

    def __init__(self, db):
        self.db = db

    async def get_by_user_id(self, user_id: int):

        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(
                Subscription.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    def create(
        self,
        subscription: Subscription,
    ):
        self.db.add(subscription)

    async def list_all(self):

        result = await self.db.execute(
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .order_by(
                Subscription.start_date.desc()
            )
        )

        return result.scalars().all()
    
    def update(
        self,
        subscription: Subscription,
    ):

        self.db.add(subscription)