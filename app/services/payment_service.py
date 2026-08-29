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

    @staticmethod
    def _decode_apple_jws(token: str) -> dict:
        """
        Decode an Apple-signed JWS (JSON Web Signature) token.
        Apple signs these with ES256 — we skip signature verification here
        since the token is received directly from Apple's StoreKit on device.
        Format: base64url(header).base64url(payload).base64url(signature)
        """
        import base64, json as _json
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError(f"Not a JWS token — expected 3 parts, got {len(parts)}")
        # base64url decode the payload (middle part)
        payload_b64 = parts[1]
        # Add padding if needed
        padding_needed = 4 - len(payload_b64) % 4
        if padding_needed != 4:
            payload_b64 += '=' * padding_needed
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return _json.loads(payload_bytes.decode('utf-8'))

    async def verify_apple_receipt(
        self,
        receipt_data: str,
        user,
    ):
        receipt_data = receipt_data.strip()

        logger.info(f"[Apple IAP] Received data length: {len(receipt_data)}")
        logger.info(f"[Apple IAP] First 40 chars: {receipt_data[:40]}")

        # Decode the StoreKit 2 JWS signed transaction token.
        # Flutter's in_app_purchase on iOS 15+ returns this as serverVerificationData.
        # Format: base64url(header).base64url(payload).base64url(signature)
        logger.info("[Apple IAP] Decoding StoreKit 2 JWS token")
        try:
            tx = self._decode_apple_jws(receipt_data)
        except Exception as e:
            logger.error(f"[Apple IAP] Failed to decode JWS token: {e}")
            raise HTTPException(status_code=400, detail="Invalid transaction token")

        product_id = tx.get("productId")
        transaction_id = tx.get("transactionId", "")
        original_transaction_id = tx.get("originalTransactionId", transaction_id)
        expires_ms = tx.get("expiresDate")
        environment = tx.get("environment", "unknown")

        logger.info(
            f"[Apple IAP] JWS decoded ✓ — "
            f"product: {product_id}, "
            f"tx: {transaction_id}, "
            f"env: {environment}"
        )

        end_date = None
        if expires_ms:
            end_date = datetime.fromtimestamp(int(expires_ms) / 1000, tz=timezone.utc)

        # Look up the matching plan in DB using the Apple product ID
        plan = await self.plan_repo.get_by_apple_product_id(product_id)
        if not plan:
            logger.error(f"[Apple IAP] No plan found for product_id: {product_id}")
            raise HTTPException(
                status_code=404,
                detail=f"No active plan found for Apple product: {product_id}",
            )

        logger.info(f"[Apple IAP] Matched plan: {plan.name} (id={plan.id})")

        # Avoid duplicate payment records and prevent stealing subscriptions
        existing = await self.payment_repo.get_by_session(transaction_id)
        existing_sub = await self.payment_repo.get_by_subscription(original_transaction_id)
        
        # Check if this Apple ID's subscription is already tied to another user
        conflict_payment = existing if existing else existing_sub
        if conflict_payment and conflict_payment.user_id != user.id:
            logger.error(f"[Apple IAP] Transaction is already claimed by user {conflict_payment.user_id} (current user: {user.id})")
            raise HTTPException(
                status_code=400,
                detail="This Apple ID is already associated with another account.",
            )
            
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

        # Upgrade the user's subscription
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
        logger.info(f"[Apple IAP] ✅ Subscription activated for user {user.id} — plan: {plan.name}")

        return {
            "success": True,
            "plan": plan.name,
            "expires_at": end_date.isoformat() if end_date else None,
        }

    async def handle_apple_webhook(
        self,
        payload: dict,
    ):
        logger.info(f"[Apple Webhook] Received — keys: {list(payload.keys())}")

        # Apple V2 Server Notifications wrap everything in a signedPayload JWS.
        # Decode it first to get the actual notification data.
        signed_payload = payload.get("signedPayload")
        if signed_payload:
            logger.info("[Apple Webhook] Decoding V2 signedPayload JWS")
            try:
                notification = self._decode_apple_jws(signed_payload)
                logger.info(f"[Apple Webhook] Decoded notification keys: {list(notification.keys())}")
            except Exception as e:
                logger.error(f"[Apple Webhook] Failed to decode signedPayload: {e}")
                return {"received": True}

            notification_type = notification.get("notificationType", "")
            subtype = notification.get("subtype", "")
            logger.info(f"[Apple Webhook] Type: {notification_type} / Subtype: {subtype}")

            # Decode the transaction info from data.signedTransactionInfo
            data = notification.get("data", {})
            signed_tx = data.get("signedTransactionInfo") or data.get("signedRenewalInfo")
            tx = {}
            if signed_tx:
                try:
                    tx = self._decode_apple_jws(signed_tx)
                    logger.info(f"[Apple Webhook] Transaction: product={tx.get('productId')}, tx={tx.get('transactionId')}")
                except Exception as e:
                    logger.error(f"[Apple Webhook] Failed to decode signedTransactionInfo: {e}")

            product_id = tx.get("productId")
            original_transaction_id = tx.get("originalTransactionId")
            expires_ms = tx.get("expiresDate")

        else:
            # Legacy V1 format (plain JSON)
            logger.info("[Apple Webhook] Using legacy V1 format")
            notification_type = payload.get("notificationType") or payload.get("notification_type", "")
            data = payload.get("data", {})
            product_id = data.get("productId") or payload.get("product_id")
            original_transaction_id = data.get("originalTransactionId") or payload.get("original_transaction_id")
            expires_ms = None

        logger.info(f"[Apple Webhook] Processing: {notification_type}, product: {product_id}, orig_tx: {original_transaction_id}")

        end_date = None
        if expires_ms:
            end_date = datetime.fromtimestamp(int(expires_ms) / 1000, tz=timezone.utc)

        # Subscription activated or renewed → upgrade user
        if notification_type in ("SUBSCRIBED", "DID_RENEW", "DID_RECOVER", "DID_CHANGE_RENEWAL_STATUS"):
            if product_id and original_transaction_id:
                plan = await self.plan_repo.get_by_apple_product_id(product_id)
                if plan:
                    payment = await self.payment_repo.get_by_subscription(original_transaction_id)
                    if payment:
                        subscription = await self.subscription_repo.get_by_user_id(payment.user_id)
                        if subscription:
                            subscription.plan_id = plan.id
                            subscription.status = SubscriptionStatus.ACTIVE
                            if end_date:
                                subscription.end_date = end_date
                            await self.db.commit()
                            logger.info(f"[Apple Webhook] ✅ Subscription activated for user {payment.user_id}")
                    else:
                        logger.warning(f"[Apple Webhook] No payment found for original_tx: {original_transaction_id}")

        # Subscription expired or cancelled → downgrade to Free Plan
        elif notification_type in ("DID_FAIL_TO_RENEW", "EXPIRED", "REVOKE", "CANCEL"):
            if original_transaction_id:
                payment = await self.payment_repo.get_by_subscription(original_transaction_id)
                if payment:
                    subscription = await self.subscription_repo.get_by_user_id(payment.user_id)
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
