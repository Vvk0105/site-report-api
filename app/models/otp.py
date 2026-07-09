from datetime import datetime

from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.db.database import Base

from app.models.base import TimestampMixin


class OTPCode(Base, TimestampMixin):

    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )

    otp: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )