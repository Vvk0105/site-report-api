from sqlalchemy import select

from app.models.plan import Plan


class PlanRepository:

    def __init__(self, db):
        self.db = db

    def create(self, plan: Plan) -> None:
        self.db.add(plan)

    def update(self, plan: Plan) -> None:
        self.db.add(plan)

    async def delete(self, plan: Plan) -> None:
        await self.db.delete(plan)

    async def get_by_id(self, plan_id: int) -> Plan | None:
        result = await self.db.execute(select(Plan).where(Plan.id == plan_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Plan]:
        result = await self.db.execute(select(Plan).order_by(Plan.created_at.desc(), Plan.id.desc()))
        return list(result.scalars().all())

    async def list_public(self) -> list[Plan]:
        """Only plans a customer can buy, filtered in SQL."""
        result = await self.db.execute(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price, Plan.id)
        )
        return list(result.scalars().all())

    async def get_trial_plan(self) -> Plan | None:
        result = await self.db.execute(
            select(Plan)
            .where(Plan.is_trial.is_(True), Plan.is_active.is_(True))
            .order_by(Plan.id)
            .limit(1)
        )
        return result.scalars().first()

    async def get_by_apple_product_id(self, apple_product_id: str) -> Plan | None:
        result = await self.db.execute(
            select(Plan).where(
                Plan.apple_product_id == apple_product_id,
                Plan.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
