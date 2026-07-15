from fastapi import HTTPException

from app.repositories.plan_repository import PlanRepository
from app.services.stripe_service import StripeService
from app.models.payment import Payment
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository

class PaymentService:

    def __init__(
        self,
        db,
    ):

        self.db = db

        self.plan_repo = PlanRepository(db)

        self.stripe = StripeService()

        self.payment_repo = PaymentRepository(db)

        self.subscription_repo = SubscriptionRepository(db)

    async def checkout(
        self,
        *,
        plan_id,
        user,
    ):

        plan = await self.plan_repo.get_by_id(
            plan_id,
        )

        if not plan:

            raise HTTPException(
                404,
                "Plan not found",
            )

        if not plan.is_active:

            raise HTTPException(
                400,
                "Plan is inactive",
            )

        session = self.stripe.create_checkout_session(
            plan=plan,
            user=user,
        )

        return {
            "checkout_url": session.url,
            "session_id": session.id,
        }
    
    async def webhook(
        self,
        payload,
        signature,
    ):

        event = self.stripe.verify_webhook(
            payload,
            signature,
        )

        if event["type"] != "checkout.session.completed":

            return {
                "received": True,
            }

        session = event["data"]["object"]

        exists = await self.payment_repo.get_by_session(
            session["id"],
        )

        if exists:

            return {
                "received": True,
            }

        user_id = int(
            session["metadata"]["user_id"]
        )

        plan_id = int(
            session["metadata"]["plan_id"]
        )

        payment = Payment(

            user_id=user_id,

            plan_id=plan_id,

            stripe_session_id=session["id"],

            stripe_customer_id=session["customer"],

            stripe_subscription_id=session["subscription"],

            amount=session["amount_total"] / 100,

            currency=session["currency"],

            status="paid",
        )

        self.payment_repo.create(
            payment,
        )

        subscription = await self.subscription_repo.get_by_user_id(
            user_id,
        )

        subscription.plan_id = plan_id

        await self.db.commit()

        return {
            "received": True,
        }