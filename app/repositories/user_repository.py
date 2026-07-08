from sqlalchemy import select

from app.models.user import User


class UserRepository:

    def __init__(self, db):
        self.db = db

    async def get_by_email(self, email: str):

        result = await self.db.execute(
            select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()

    async def create(self, user):

        self.db.add(user)

        await self.db.commit()

        await self.db.refresh(user)

        return user