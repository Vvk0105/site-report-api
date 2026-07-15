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