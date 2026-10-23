import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException

from app.enums.payment import PaymentStatus
from app.enums.subscription import SubscriptionStatus
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.apple_jws import AppleVerificationError, verify_jws
from app.services.stripe_service import StripeService
from app.utils.pagination import paginate

logger = logging.getLogger("site-report")

APPLE_CURRENCY_FALLBACK = "USD"

# Stripe subscription status -> local status. `past_due` is intentionally absent:
# the customer keeps access during Stripe's retry window.
STRIPE_STATUS_MAP = {
    "active": SubscriptionStatus.ACTIVE,
    "trialing": SubscriptionStatus.ACTIVE,
    "canceled": SubscriptionStatus.CANCELLED,
    "unpaid": SubscriptionStatus.CANCELLED,
    "incomplete_expired": SubscriptionStatus.CANCELLED,
}


def _ms_to_datetime(value) -> datetime | None:
    if not value:
        return None
    return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)


class PaymentService:

    def __init__(self, db):
        self.db = db
        self.plan_repo = PlanRepository(db)
        self.stripe = StripeService()
        self.payment_repo = PaymentRepository(db)
        self.subscription_repo = SubscriptionRepository(db)
        self.user_repo = UserRepository(db)

    # ─── helpers ───────────────────────────────────────────────────────────

    async def _upsert_subscription(
        self,
        user_id: int,
        plan,
        status: SubscriptionStatus,
        *,
        end_date: datetime | None = None,
        reset_start: bool = True,
    ) -> Subscription:
        subscription = await self.subscription_repo.get_by_user_id(user_id, lock=True)

        if subscription is None:
            subscription = Subscription(
                user_id=user_id,
                plan_id=plan.id,
                status=status,
                start_date=datetime.now(timezone.utc),
                end_date=end_date,
            )
            self.subscription_repo.create(subscription)
        else:
            subscription.plan_id = plan.id
            if reset_start:
                subscription.start_date = datetime.now(timezone.utc)
            if end_date is not None:
                subscription.end_date = end_date
            subscription.status = status

        # Keep the relationship in sync; otherwise the response still shows the old plan.
        subscription.plan = plan
        return subscription

    async def _payment_exists(self, stripe_session_id: str) -> bool:
        return await self.payment_repo.get_by_session(stripe_session_id) is not None

    # ─── customer checkout ─────────────────────────────────────────────────

    async def checkout(self, *, plan_id: int, user) -> dict:
        plan = await self.plan_repo.get_by_id(plan_id)

        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")

        if not plan.is_active:
            raise HTTPException(status_code=400, detail="Plan is inactive")

        if not user.stripe_customer_id:
            customer = await asyncio.to_thread(
                self.stripe.create_customer,
                email=user.email,
                name=user.full_name,
            )
            user.stripe_customer_id = customer.id
            self.user_repo.update(user)
            await self.db.commit()

        session = await asyncio.to_thread(
            self.stripe.create_checkout_session,
            plan=plan,
            user=user,
        )

        return {"checkout_url": session.url, "session_id": session.id}

    # ─── Stripe webhook ────────────────────────────────────────────────────

    async def webhook(self, payload: bytes, signature: str) -> dict:
        try:
            event = await asyncio.to_thread(self.stripe.verify_webhook, payload, signature)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid Stripe signature")

        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "checkout.session.completed":
            await self._on_checkout_completed(data)

        elif event_type == "invoice.paid":
            await self._on_invoice_paid(data)

        elif event_type == "customer.subscription.updated":
            await self._on_subscription_updated(data)

        elif event_type == "customer.subscription.deleted":
            await self._on_subscription_deleted(data)

        return {"received": True}

    async def _on_checkout_completed(self, data: dict) -> None:
        if await self._payment_exists(data["id"]):
            return

        metadata = data.get("metadata") or {}
        if not metadata.get("user_id") or not metadata.get("plan_id") or not data.get("subscription"):
            logger.warning("checkout.session.completed without usable metadata (session=%s)", data["id"])
            return

        user_id = int(metadata["user_id"])
        plan = await self.plan_repo.get_by_id(int(metadata["plan_id"]))
        if not plan:
            logger.error("checkout.session.completed for unknown plan (session=%s)", data["id"])
            return

        self.payment_repo.create(
            Payment(
                user_id=user_id,
                plan_id=plan.id,
                stripe_customer_id=data["customer"],
                stripe_session_id=data["id"],
                stripe_subscription_id=data["subscription"],
                stripe_payment_intent=data.get("payment_intent"),
                amount=Decimal(data["amount_total"]) / 100,
                currency=data["currency"].upper(),
                status=PaymentStatus.PAID,
            )
        )

        await self._upsert_subscription(user_id, plan, SubscriptionStatus.ACTIVE)
        await self.db.commit()

    async def _on_invoice_paid(self, invoice: dict) -> None:
        # The first invoice is already recorded from checkout.session.completed.
        if invoice.get("billing_reason") != "subscription_cycle":
            return

        if await self._payment_exists(invoice["id"]):
            return

        user = await self.user_repo.get_by_stripe_customer_id(invoice["customer"])
        subscription = await self.subscription_repo.get_by_user_id(user.id) if user else None
        if not subscription:
            logger.warning("Renewal invoice %s has no matching local subscription", invoice["id"])
            return

        self.payment_repo.create(
            Payment(
                user_id=user.id,
                plan_id=subscription.plan_id,
                stripe_customer_id=invoice["customer"],
                # Renewals have no checkout session; the invoice id keeps the row unique.
                stripe_session_id=invoice["id"],
                stripe_subscription_id=invoice.get("subscription") or "",
                stripe_payment_intent=invoice.get("payment_intent"),
                amount=Decimal(invoice["amount_paid"]) / 100,
                currency=invoice["currency"].upper(),
                status=PaymentStatus.PAID,
            )
        )
        await self.db.commit()

    async def _on_subscription_updated(self, data: dict) -> None:
        user = await self.user_repo.get_by_stripe_customer_id(data["customer"])
        if not user:
            return

        subscription = await self.subscription_repo.get_by_user_id(user.id, lock=True)
        if not subscription:
            return

        status = STRIPE_STATUS_MAP.get(data.get("status"))
        if status is not None:
            subscription.status = status

        if data.get("current_period_end"):
            subscription.end_date = datetime.fromtimestamp(data["current_period_end"], tz=timezone.utc)

        await self.db.commit()

    async def _on_subscription_deleted(self, data: dict) -> None:
        user = await self.user_repo.get_by_stripe_customer_id(data["customer"])
        if not user:
            return

        subscription = await self.subscription_repo.get_by_user_id(user.id, lock=True)
        if subscription:
            subscription.status = SubscriptionStatus.CANCELLED
            await self.db.commit()

    # ─── customer reads ────────────────────────────────────────────────────

    async def history(self, user):
        return await self.payment_repo.history(user.id)

    async def admin_payments(self, page: int, page_size: int) -> dict:
        """Paginated list for the admin panel."""
        total, payments = await self.payment_repo.admin_list(page, page_size)

        results = [
            {
                "id": payment.id,
                "user_id": payment.user_id,
                "user_email": payment.user.email,
                "plan": payment.plan.name,
                "amount": float(payment.amount),
                "currency": payment.currency,
                "status": payment.status.value,
                "stripe_session_id": payment.stripe_session_id,
                "created_at": payment.created_at,
            }
            for payment in payments
        ]

        return paginate(total=total, page=page, page_size=page_size, results=results)

    async def verify(self, session_id: str) -> dict:
        """Public endpoint used by the post-checkout page. Returns only what the page needs."""
        payment = await self.payment_repo.get_by_session(session_id)

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        return {
            "paid": payment.status == PaymentStatus.PAID,
            "status": payment.status.value,
        }

    async def customer_portal(self, user) -> dict:
        if not user.stripe_customer_id:
            raise HTTPException(status_code=400, detail="Customer not found")

        url = await asyncio.to_thread(self.stripe.create_customer_portal, user.stripe_customer_id)
        return {"url": url}

    # ─── Apple ─────────────────────────────────────────────────────────────

    @staticmethod
    def _verified_transaction(token: str) -> dict:
        try:
            return verify_jws(token)
        except AppleVerificationError as exc:
            logger.error("[Apple IAP] Rejected token: %s", exc)
            raise HTTPException(status_code=400, detail="Invalid transaction token")

    async def verify_apple_receipt(self, receipt_data: str, user) -> dict:
        tx = self._verified_transaction(receipt_data.strip())

        product_id = tx.get("productId")
        transaction_id = tx.get("transactionId")
        original_transaction_id = tx.get("originalTransactionId") or transaction_id

        if not product_id or not transaction_id:
            raise HTTPException(status_code=400, detail="Invalid transaction token")

        # 409 "stale_receipt" tells the app this transaction can never grant access,
        # so it finishes the StoreKit transaction instead of replaying it forever.
        if tx.get("revocationDate"):
            raise HTTPException(status_code=409, detail="stale_receipt")

        end_date = _ms_to_datetime(tx.get("expiresDate"))
        if end_date and end_date < datetime.now(timezone.utc):
            raise HTTPException(status_code=409, detail="stale_receipt")

        plan = await self.plan_repo.get_by_apple_product_id(product_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Product not recognized. Please contact support.")

        # An Apple subscription can only belong to one account.
        owner = await self.payment_repo.get_by_session(transaction_id)
        if owner is None:
            owner = await self.payment_repo.latest_by_subscription(original_transaction_id)
        if owner and owner.user_id != user.id:
            raise HTTPException(
                status_code=400,
                detail="This Apple ID is already associated with another account.",
            )

        if not owner:
            self.payment_repo.create(
                Payment(
                    user_id=user.id,
                    plan_id=plan.id,
                    stripe_customer_id="apple_iap",
                    stripe_session_id=transaction_id,
                    stripe_subscription_id=original_transaction_id,
                    amount=Decimal(str(plan.price)),
                    currency=plan.currency or APPLE_CURRENCY_FALLBACK,
                    status=PaymentStatus.PAID,
                )
            )

        await self._upsert_subscription(user.id, plan, SubscriptionStatus.ACTIVE, end_date=end_date)
        await self.db.commit()

        return {
            "success": True,
            "plan": plan.name,
            "expires_at": end_date.isoformat() if end_date else None,
        }

    async def handle_apple_webhook(self, payload: dict) -> dict:
        signed_payload = payload.get("signedPayload")
        if not signed_payload:
            raise HTTPException(status_code=400, detail="Missing signedPayload")

        try:
            notification = verify_jws(signed_payload)
        except AppleVerificationError as exc:
            # Refuse unverified notifications. Returning an error makes Apple retry.
            logger.error("[Apple Webhook] Rejected notification: %s", exc)
            raise HTTPException(status_code=400, detail="Invalid notification signature")

        notification_type = notification.get("notificationType", "")
        data = notification.get("data") or {}

        tx = {}
        if data.get("signedTransactionInfo"):
            tx = self._verified_transaction(data["signedTransactionInfo"])

        product_id = tx.get("productId")
        original_transaction_id = tx.get("originalTransactionId")
        transaction_id = tx.get("transactionId")
        end_date = _ms_to_datetime(tx.get("expiresDate"))

        logger.info("[Apple Webhook] %s product=%s", notification_type, product_id)

        if not original_transaction_id:
            return {"received": True}

        owner_payment = await self.payment_repo.latest_by_subscription(original_transaction_id)
        if not owner_payment:
            logger.warning("[Apple Webhook] No local payment for original transaction %s", original_transaction_id)
            return {"received": True}

        user_id = owner_payment.user_id

        if notification_type in ("SUBSCRIBED", "DID_RENEW", "DID_RECOVER"):
            plan = await self.plan_repo.get_by_apple_product_id(product_id) if product_id else None
            if plan:
                if transaction_id and not await self._payment_exists(transaction_id):
                    self.payment_repo.create(
                        Payment(
                            user_id=user_id,
                            plan_id=plan.id,
                            stripe_customer_id="apple_iap",
                            stripe_session_id=transaction_id,
                            stripe_subscription_id=original_transaction_id,
                            amount=Decimal(str(plan.price)),
                            currency=plan.currency or APPLE_CURRENCY_FALLBACK,
                            status=PaymentStatus.PAID,
                        )
                    )
                await self._upsert_subscription(
                    user_id,
                    plan,
                    SubscriptionStatus.ACTIVE,
                    end_date=end_date,
                    reset_start=notification_type == "SUBSCRIBED",
                )

        elif notification_type in ("EXPIRED", "DID_FAIL_TO_RENEW", "REFUND", "REVOKE"):
            subscription = await self.subscription_repo.get_by_user_id(user_id, lock=True)
            if subscription:
                trial_plan = await self.plan_repo.get_trial_plan()
                if trial_plan:
                    subscription.plan = trial_plan
                    subscription.plan_id = trial_plan.id
                subscription.status = SubscriptionStatus.CANCELLED
                subscription.end_date = datetime.now(timezone.utc)

        await self.db.commit()
        return {"received": True}
