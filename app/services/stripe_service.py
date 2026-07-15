import stripe

from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:

    def create_product_and_price(
        self,
        *,
        name: str,
        description: str | None,
        price: float,
        currency: str,
        billing_cycle: str,
    ):

        product = stripe.Product.create(
            name=name,
            description=description,
        )

        stripe_price = stripe.Price.create(
            product=product.id,
            unit_amount=int(price * 100),
            currency=currency.lower(),
            recurring={
                "interval": billing_cycle,
            },
        )

        return (
            product.id,
            stripe_price.id,
        )
    
    def create_checkout_session(
        self,
        *,
        plan,
        user,
    ):

        session = stripe.checkout.Session.create(

            mode="subscription",

            customer_email=user.email,

            line_items=[
                {
                    "price": plan.stripe_price_id,
                    "quantity": 1,
                }
            ],

            success_url="https://sitesreports.com/payment-success?session_id={CHECKOUT_SESSION_ID}",

            cancel_url="https://sitesreports.com/payment-cancel",

            metadata={
                "user_id": user.id,
                "plan_id": plan.id,
            },
        )

        return session
    
    def verify_webhook(
        self,
        payload,
        signature,
    ):

        return stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )