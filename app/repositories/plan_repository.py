from sqlalchemy import select

from app.models.plan import Plan


class PlanRepository:

    def __init__(
        self,
        db,
    ):
        self.db = db

    async def get_all_active(
        self,
    ):

        result = await self.db.execute(
            select(Plan).where(
                Plan.is_active == True,
            )
        )

        return result.scalars().all()

    async def get_by_id(
        self,
        plan_id: int,
    ):

        result = await self.db.execute(
            select(Plan).where(
                Plan.id == plan_id,
            )
        )

        return result.scalar_one_or_none()

    def create(
        self,
        plan: Plan,
    ):

        self.db.add(plan)