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

        interval_map = {
            "monthly": "month",
            "yearly": "year",
            "weekly": "week",
            "daily": "day",
        }
        
        price_kwargs = {
            "product": product.id,
            "unit_amount": int(price * 100),
            "currency": currency.lower(),
        }
        
        if billing_cycle != "lifetime":
            interval = interval_map.get(billing_cycle, billing_cycle)
            price_kwargs["recurring"] = {"interval": interval}

        stripe_price = stripe.Price.create(**price_kwargs)

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

            customer=user.stripe_customer_id,

            line_items=[
                {
                    "price": plan.stripe_price_id,
                    "quantity": 1,
                }
            ],

            success_url="https://admin.sitesreports.com/payment-success?session_id={CHECKOUT_SESSION_ID}",

            cancel_url="https://admin.sitesreports.com/payment-cancel",

            metadata={
                "user_id": user.id,
                "plan_id": plan.id,
            },
        )

        return session
    
    def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ):

        return stripe.Webhook.construct_event(
            payload,
            signature,
            settings.STRIPE_WEBHOOK_SECRET,
        )
    
    def create_customer(
        self,
        *,
        email: str,
        name: str | None,
    ):

        customer = stripe.Customer.create(
            email=email,
            name=name,
        )

        return customer
    
    def create_customer_portal(
        self,
        customer_id: str,
    ):

        session = stripe.billing_portal.Session.create(

            customer=customer_id,

            return_url="https://sitesreports.com/profile",
        )

        return session.url