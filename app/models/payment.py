from sqlalchemy import ForeignKey
from sqlalchemy import Numeric
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.database import Base
from app.models.base import TimestampMixin
from sqlalchemy.orm import relationship

class Payment(
    Base,
    TimestampMixin,
):

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id"),
    )

    stripe_customer_id: Mapped[str] = mapped_column(
        String(255),
    )

    stripe_session_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
    )

    stripe_subscription_id: Mapped[str] = mapped_column(
        String(255),
    )

    stripe_payment_intent: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    amount: Mapped[float] = mapped_column(
        Numeric(10, 2),
    )

    currency: Mapped[str] = mapped_column(
        String(10),
    )

    status: Mapped[str] = mapped_column(
        String(30),
    )

    user = relationship(
        "User",
    )

    plan = relationship(
        "Plan",
    )