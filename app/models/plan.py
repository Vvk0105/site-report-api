from sqlalchemy import Boolean
from sqlalchemy import Numeric
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.database import Base
from app.models.base import TimestampMixin


class Plan(
    Base,
    TimestampMixin,
):

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    price: Mapped[float] = mapped_column(
        Numeric(10, 2),
    )

    currency: Mapped[str] = mapped_column(
        String(10),
        default="AUD",
    )

    billing_cycle: Mapped[str] = mapped_column(
        String(20),
    )

    report_limit: Mapped[int] = mapped_column()

    trial_days: Mapped[int] = mapped_column(
        default=0,
    )

    is_trial: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    stripe_product_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    stripe_price_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )