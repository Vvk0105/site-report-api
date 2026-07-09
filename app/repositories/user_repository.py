from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_email(self, email: str):

        result = await self.db.execute(
            select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()

    def create(
        self,
        user: User,
    ):
        self.db.add(user)


    async def get_by_id(
        self,
        user_id: int,
    ):

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )

        return result.scalar_one_or_none()
    
    async def exists_by_email(self, email: str) -> bool:

        result = await self.db.execute(
            select(User.id).where(User.email == email)
        )

        return result.scalar_one_or_none() is not None