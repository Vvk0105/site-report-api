from fastapi import HTTPException

from app.models.plan import Plan
from app.repositories.plan_repository import PlanRepository
from app.services.stripe_service import StripeService

class PlanService:

    def __init__(
        self,
        db,
    ):

        self.db = db
        self.repo = PlanRepository(db)
        self.stripe = StripeService()

    async def list(self):

        return await self.repo.list()

    async def create(
        self,
        request,
    ):

        product_id, price_id = (
            self.stripe.create_product_and_price(
                name=request.name,
                description=request.description,
                price=float(request.price),
                currency=request.currency,
                billing_cycle=request.billing_cycle,
            )
        )
        
        plan = Plan(
            **request.model_dump(),
            stripe_product_id=product_id,
            stripe_price_id=price_id,
        )

        self.repo.create(plan)

        await self.db.commit()

        await self.db.refresh(plan)

        return plan

    async def update(
        self,
        plan_id,
        request,
    ):

        plan = await self.repo.get_by_id(
            plan_id,
        )

        if not plan:

            raise HTTPException(
                404,
                "Plan not found",
            )

        for key, value in request.model_dump().items():

            setattr(
                plan,
                key,
                value,
            )

        self.repo.update(plan)

        await self.db.commit()

        await self.db.refresh(plan)

        return plan

    async def delete(
        self,
        plan_id,
    ):

        plan = await self.repo.get_by_id(
            plan_id,
        )

        if not plan:

            raise HTTPException(
                404,
                "Plan not found",
            )

        plan.is_active = False

        self.repo.update(plan)

        await self.db.commit()

        return {
            "message": "Plan deleted successfully",
        }