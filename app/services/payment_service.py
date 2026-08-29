import httpx
import logging

logger = logging.getLogger(__name__)

from fastapi import HTTPException

from app.repositories.plan_repository import PlanRepository
from app.services.stripe_service import StripeService
from app.models.payment import Payment
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
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

        self.user_repo = UserRepository(db)

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

        event_type = event["type"]

        data = event["data"]["object"]

        if event_type == "checkout.session.completed":

            exists = await self.payment_repo.get_by_session(
                data["id"],
            )

            if exists:
                return {
                    "received": True,
                }

            user_id = int(
                data["metadata"]["user_id"]
            )

            plan_id = int(
                data["metadata"]["plan_id"]
            )

            payment = Payment(
                user_id=user_id,
                plan_id=plan_id,
                stripe_customer_id=data["customer"],
                stripe_session_id=data["id"],
                stripe_subscription_id=data["subscription"],
                stripe_payment_intent=data.get(
                    "payment_intent"
                ),
                amount=data["amount_total"] / 100,
                currency=data["currency"].upper(),
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

            await self.db.commit()

        elif event_type == "customer.subscription.deleted":

            stripe_subscription = data["id"]

            payment = await self.payment_repo.get_by_subscription(
                stripe_subscription,
            )

            if payment:

                subscription = await self.subscription_repo.get_by_user_id(
                    payment.user_id,
                )

                subscription.status = SubscriptionStatus.CANCELLED

                await self.db.commit()

        elif event_type == "customer.subscription.updated":

            stripe_subscription = data["id"]

            payment = await self.payment_repo.get_by_subscription(
                stripe_subscription,
            )

            if payment:

                subscription = await self.subscription_repo.get_by_user_id(
                    payment.user_id,
                )

                subscription.status = SubscriptionStatus.ACTIVE

                if data.get(
                    "current_period_end"
                ):

                    subscription.end_date = datetime.fromtimestamp(
                        data["current_period_end"],
                        tz=timezone.utc,
                    )

                await self.db.commit()

        elif event_type == "invoice.paid":

            pass

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
    
    async def customer_portal(
        self,
        user,
    ):

        if not user.stripe_customer_id:

            raise HTTPException(
                400,
                "Customer not found",
            )

        return {
            "url": self.stripe.create_customer_portal(
                user.stripe_customer_id,
            )
        }

    async def verify_apple_receipt(
        self,
        receipt_data: str,
        user,
    ):
        from app.core.config import settings

        # Strip ALL whitespace including embedded newlines.
        # StoreKit sometimes wraps base64 with line breaks → Apple returns 21002.
        receipt_data = receipt_data.strip().replace('\n', '').replace('\r', '').replace(' ', '')

        payload = {
            "receipt-data": receipt_data,
            "password": settings.APPLE_SHARED_SECRET,
            "exclude-old-transactions": True,
        }

        # Always try production first
        logger.info("[Apple IAP] Sending receipt to PRODUCTION endpoint")
        logger.info(f"[Apple IAP] Shared secret set: {bool(settings.APPLE_SHARED_SECRET)}")
        logger.info(f"[Apple IAP] Receipt data length: {len(receipt_data)}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://buy.itunes.apple.com/verifyReceipt",
                json=payload,
            )
            result = resp.json()

        apple_status = result.get("status")
        logger.info(f"[Apple IAP] Production response status: {apple_status}")

        # Status 21007 = sandbox receipt sent to production → retry sandbox
        if apple_status == 21007:
            logger.info("[Apple IAP] Sandbox receipt detected — retrying with SANDBOX endpoint")
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://sandbox.itunes.apple.com/verifyReceipt",
                    json=payload,
                )
                result = resp.json()
            apple_status = result.get("status")
            logger.info(f"[Apple IAP] Sandbox response status: {apple_status}")

        if apple_status == 21002:
            # Stale/malformed receipt — usually a stuck pending transaction replaying.
            # Return 422 so Flutter knows to call completePurchase() and clear it.
            logger.error("[Apple IAP] Status 21002 — stale or malformed receipt (stuck pending transaction)")
            raise HTTPException(
                status_code=422,
                detail="stale_receipt",
            )

        if apple_status != 0:
            logger.error(f"[Apple IAP] Verification FAILED — Apple status: {apple_status}")
            raise HTTPException(
                status_code=400,
                detail=f"Apple receipt verification failed: status {apple_status}",
            )
        logger.info("[Apple IAP] Receipt verified successfully!")

        latest_list = result.get("latest_receipt_info", [])
        if not latest_list:
            raise HTTPException(
                status_code=400,
                detail="No receipt info found",
            )

        # Use the most recent transaction
        latest = latest_list[-1]
        product_id = latest.get("product_id")

        # Find the matching plan in DB
        plan = await self.plan_repo.get_by_apple_product_id(product_id)
        if not plan:
            raise HTTPException(
                status_code=404,
                detail=f"No active plan found for Apple product: {product_id}",
            )

        # Parse subscription end date from Apple's epoch-ms timestamp
        expires_ms = latest.get("expires_date_ms")
        end_date = None
        if expires_ms:
            end_date = datetime.fromtimestamp(
                int(expires_ms) / 1000,
                tz=timezone.utc,
            )

        transaction_id = latest.get("transaction_id", "")
        original_transaction_id = latest.get(
            "original_transaction_id", transaction_id
        )

        # Avoid duplicate payment records
        existing = await self.payment_repo.get_by_session(transaction_id)
        if not existing:
            payment = Payment(
                user_id=user.id,
                plan_id=plan.id,
                stripe_customer_id="apple_iap",
                stripe_session_id=transaction_id,
                stripe_subscription_id=original_transaction_id,
                amount=float(plan.price),
                currency="USD",
                status=PaymentStatus.PAID,
            )
            self.payment_repo.create(payment)

        # Upgrade the user's subscription (create one if it doesn't exist)
        from app.models.subscription import Subscription
        subscription = await self.subscription_repo.get_by_user_id(user.id)
        if subscription is None:
            subscription = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                status=SubscriptionStatus.ACTIVE,
                start_date=datetime.now(timezone.utc),
                end_date=end_date,
            )
            self.subscription_repo.create(subscription)
        else:
            subscription.plan_id = plan.id
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.start_date = datetime.now(timezone.utc)
            subscription.end_date = end_date

        await self.db.commit()

        return {
            "success": True,
            "plan": plan.name,
            "expires_at": end_date.isoformat() if end_date else None,
        }

    async def handle_apple_webhook(
        self,
        payload: dict,
    ):
        from app.core.config import settings

        notification_type = payload.get(
            "notificationType"
        ) or payload.get("notification_type", "")

        logger.info(f"[Apple Webhook] Received notification: {notification_type}")
        logger.info(f"[Apple Webhook] Full payload keys: {list(payload.keys())}")

        # Subscription activated or renewed → upgrade user
        if notification_type in ("SUBSCRIBED", "DID_RENEW", "DID_RECOVER"):
            data = payload.get("data", {})
            transaction_info = data.get("transactionInfo") or data.get("transaction_info") or {}
            original_transaction_id = (
                transaction_info.get("originalTransactionId")
                or data.get("originalTransactionId")
                or payload.get("original_transaction_id")
            )
            product_id = (
                transaction_info.get("productId")
                or data.get("productId")
                or payload.get("product_id")
            )
            logger.info(f"[Apple Webhook] SUBSCRIBED/RENEW — original_tx: {original_transaction_id}, product: {product_id}")

            if original_transaction_id and product_id:
                plan = await self.plan_repo.get_by_apple_product_id(product_id)
                if plan:
                    payment = await self.payment_repo.get_by_subscription(original_transaction_id)
                    if payment:
                        subscription = await self.subscription_repo.get_by_user_id(payment.user_id)
                        if subscription:
                            subscription.plan_id = plan.id
                            subscription.status = SubscriptionStatus.ACTIVE
                            await self.db.commit()
                            logger.info(f"[Apple Webhook] Subscription activated for user {payment.user_id}")

        # Subscription expired or cancelled → downgrade to Free Plan
        elif notification_type in (
            "DID_FAIL_TO_RENEW",
            "EXPIRED",
            "REVOKE",
            "CANCEL",
        ):
            data = payload.get("data", {})
            original_transaction_id = data.get(
                "originalTransactionId"
            ) or payload.get("original_transaction_id")

            if original_transaction_id:
                payment = await self.payment_repo.get_by_subscription(
                    original_transaction_id
                )
                if payment:
                    subscription = (
                        await self.subscription_repo.get_by_user_id(
                            payment.user_id
                        )
                    )
                    if subscription:
                        free_plan = await self.plan_repo.get_trial_plan()
                        if free_plan:
                            subscription.plan_id = free_plan.id
                        subscription.status = SubscriptionStatus.CANCELLED
                        subscription.end_date = datetime.now(timezone.utc)
                        await self.db.commit()
                        logger.info(f"[Apple Webhook] Subscription cancelled for user {payment.user_id}")
        else:
            logger.info(f"[Apple Webhook] Unhandled notification type: {notification_type}")

        return {"received": True}
