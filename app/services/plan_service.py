import asyncio
import logging
from decimal import Decimal

from fastapi import HTTPException

from app.models.plan import Plan
from app.repositories.plan_repository import PlanRepository
from app.services.stripe_service import StripeService

logger = logging.getLogger("site-report")

PRICING_FIELDS = ("price", "currency", "billing_cycle")


class PlanService:

    def __init__(self, db):
        self.db = db
        self.repo = PlanRepository(db)
        self.stripe = StripeService()

    async def list(self):
        return await self.repo.list_all()

    async def list_public(self):
        return await self.repo.list_public()

    async def create(self, request):
        product_id, price_id = await asyncio.to_thread(
            self.stripe.create_product_and_price,
            name=request.name,
            description=request.description,
            price=request.price,
            currency=request.currency,
            billing_cycle=request.billing_cycle,
        )

        plan = Plan(
            **request.model_dump(exclude={"price"}),
            price=Decimal(str(request.price)),
            stripe_product_id=product_id,
            stripe_price_id=price_id,
        )

        try:
            self.repo.create(plan)
            await self.db.commit()
        except Exception:
            # Don't leave an orphaned product behind in Stripe.
            await self.db.rollback()
            try:
                await asyncio.to_thread(self.stripe.archive_product, product_id)
            except Exception:
                logger.exception("Could not archive orphaned Stripe product %s", product_id)
            raise

        await self.db.refresh(plan)
        return plan

    async def update(self, plan_id, request):
        plan = await self.repo.get_by_id(plan_id)

        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        new_values = request.model_dump()
        new_values["price"] = Decimal(str(new_values["price"]))

        pricing_changed = any(
            getattr(plan, field) != new_values[field] for field in PRICING_FIELDS
        )

        # Stripe prices are immutable: a price change needs a new Stripe price, and
        # checkout must use it, otherwise customers keep being charged the old amount.
        if pricing_changed and plan.stripe_product_id:
            new_price = await asyncio.to_thread(
                self.stripe.create_price,
                product_id=plan.stripe_product_id,
                price=new_values["price"],
                currency=new_values["currency"],
                billing_cycle=new_values["billing_cycle"],
            )
            plan.stripe_price_id = new_price.id

        for key, value in new_values.items():
            setattr(plan, key, value)

        self.repo.update(plan)
        await self.db.commit()
        await self.db.refresh(plan)

        return plan

    async def delete(self, plan_id):
        plan = await self.repo.get_by_id(plan_id)

        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        # Soft delete: existing subscriptions still reference this plan.
        plan.is_active = False
        self.repo.update(plan)
        await self.db.commit()

        return {"message": "Plan deleted successfully"}
