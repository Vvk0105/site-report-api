from sqlalchemy import select

from app.models.subscription import Subscription


class SubscriptionRepository:

    def __init__(self, db):
        self.db = db

    async def get_by_user_id(self, user_id: int):

        result = await self.db.execute(
            select(Subscription).where(
                Subscription.user_id == user_id
            )
        )

        return result.scalar_one_or_none()

    def create(
        self,
        subscription: Subscription,
    ):
        self.db.add(subscription)