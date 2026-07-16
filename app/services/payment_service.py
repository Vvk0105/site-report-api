from fastapi import HTTPException

from app.repositories.plan_repository import PlanRepository
from app.services.stripe_service import StripeService
from app.models.payment import Payment
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from datetime import datetime
from datetime import timezone

from app.enums.subscription import SubscriptionStatus
from app.enums.payment import PaymentStatus
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

        if not user.stripe_customer_id:

            customer = self.stripe.create_customer(
                email=user.email,
                name=user.full_name,
            )

            user.stripe_customer_id = customer.id

            self.user_repo.update(
                user,
            )

            await self.db.commit()

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
        payload: bytes,
        signature: str,
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
            stripe_customer_id=session["customer"],
            stripe_session_id=session["id"],
            stripe_subscription_id=session["subscription"],
            stripe_payment_intent=session.get(
                "payment_intent"
            ),
            amount=session["amount_total"] / 100,
            currency=session["currency"].upper(),
            status=PaymentStatus.PAID,
        )

        self.payment_repo.create(
            payment,
        )

        subscription = await self.subscription_repo.get_by_user_id(
            user_id,
        )

        subscription.plan_id = plan_id
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.start_date = datetime.now(
            timezone.utc,
        )
        subscription.end_date = None

        await self.db.commit()

        return {
            "received": True,
        }
    
    async def history(
        self,
        user,
    ):

        payments = await self.payment_repo.history(
            user.id,
        )

        return payments
    
    async def admin_payments(
        self,
    ):

        payments = await self.payment_repo.admin_list()

        data = []

        for payment in payments:

            data.append(
                {
                    "id": payment.id,
                    "user_id": payment.user_id,
                    "user_email": payment.user.email,
                    "plan": payment.plan.name,
                    "amount": float(payment.amount),
                    "currency": payment.currency,
                    "status": payment.status,
                    "stripe_session_id": payment.stripe_session_id,
                    "created_at": payment.created_at,
                }
            )

        return data
    
    async def verify(
        self,
        session_id: str,
    ):

        payment = await self.payment_repo.get_by_session(
            session_id,
        )

        if not payment:

            raise HTTPException(
                status_code=404,
                detail="Payment not found",
            )

        return {
            "paid": payment.status == PaymentStatus.PAID,
            "status": payment.status.value,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "plan": payment.plan.name,
            "payment_date": payment.created_at,
        }