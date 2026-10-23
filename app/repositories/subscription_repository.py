from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.enums.subscription import SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.utils.query import escape_like


class SubscriptionRepository:

    def __init__(self, db):
        self.db = db

    async def get_by_user_id(self, user_id: int, *, lock: bool = False) -> Subscription | None:
        """
        `lock=True` takes a row lock, so two concurrent report starts cannot
        both pass the quota check.
        """
        query = (
            select(Subscription)
            .options(selectinload(Subscription.plan))
            .where(Subscription.user_id == user_id)
        )
        if lock:
            query = query.with_for_update()

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def create(self, subscription: Subscription) -> None:
        self.db.add(subscription)

    def update(self, subscription: Subscription) -> None:
        self.db.add(subscription)

    async def list_paginated(
        self,
        page: int,
        page_size: int,
        *,
        status: SubscriptionStatus | None = None,
        search: str | None = None,
    ):
        query = select(Subscription).join(User, User.id == Subscription.user_id)

        if status is not None:
            query = query.where(Subscription.status == status)

        if search:
            query = query.where(User.email.ilike(f"%{escape_like(search)}%", escape="\\"))

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))

        result = await self.db.execute(
            query.options(selectinload(Subscription.plan), selectinload(Subscription.user))
            .order_by(Subscription.start_date.desc(), Subscription.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        return total, result.scalars().all()
