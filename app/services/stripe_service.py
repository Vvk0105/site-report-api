from decimal import ROUND_HALF_UP, Decimal

import stripe

from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

INTERVAL_MAP = {
    "monthly": "month",
    "yearly": "year",
    "weekly": "week",
    "daily": "day",
}


def to_minor_units(amount) -> int:
    """Convert a decimal amount to cents without float truncation (19.99 -> 1999)."""
    return int(Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)


class StripeService:
    """
    Thin wrapper around the Stripe SDK. These methods are blocking, so callers in
    async code must run them with asyncio.to_thread.
    """

    def create_product_and_price(
        self,
        *,
        name: str,
        description: str | None,
        price,
        currency: str,
        billing_cycle: str,
    ) -> tuple[str, str]:
        product = stripe.Product.create(name=name, description=description)
        stripe_price = self.create_price(
            product_id=product.id,
            price=price,
            currency=currency,
            billing_cycle=billing_cycle,
        )
        return product.id, stripe_price.id

    def create_price(self, *, product_id: str, price, currency: str, billing_cycle: str):
        kwargs = {
            "product": product_id,
            "unit_amount": to_minor_units(price),
            "currency": currency.lower(),
        }
        if billing_cycle != "lifetime":
            kwargs["recurring"] = {"interval": INTERVAL_MAP.get(billing_cycle, "month")}
        return stripe.Price.create(**kwargs)

    def archive_product(self, product_id: str) -> None:
        stripe.Product.modify(product_id, active=False)

    def create_checkout_session(self, *, plan, user):
        if plan.stripe_price_id:
            line_items = [{"price": plan.stripe_price_id, "quantity": 1}]
        else:
            # Plans created before Stripe prices were stored fall back to inline pricing.
            interval = INTERVAL_MAP.get((plan.billing_cycle or "").lower(), "month")
            price_data = {
                "currency": (plan.currency or "AUD").lower(),
                "unit_amount": to_minor_units(plan.price),
                "recurring": {"interval": interval},
            }
            if plan.stripe_product_id:
                price_data["product"] = plan.stripe_product_id
            else:
                price_data["product_data"] = {"name": plan.name}
            line_items = [{"price_data": price_data, "quantity": 1}]

        return stripe.checkout.Session.create(
            mode="subscription",
            customer=user.stripe_customer_id,
            line_items=line_items,
            success_url=f"{settings.ADMIN_PUBLIC_URL}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{settings.ADMIN_PUBLIC_URL}/payment-cancel",
            metadata={"user_id": str(user.id), "plan_id": str(plan.id)},
        )

    def verify_webhook(self, payload: bytes, signature: str):
        return stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )

    def create_customer(self, *, email: str, name: str | None):
        return stripe.Customer.create(email=email, name=name)

    def create_customer_portal(self, customer_id: str) -> str:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{settings.WEB_PUBLIC_URL}/profile",
        )
        return session.url
