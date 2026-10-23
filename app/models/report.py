from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import UniqueConstraint

from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.enums.report import ReportStatus
from app.models.base import TimestampMixin
from sqlalchemy import Boolean

class Report(Base, TimestampMixin):

    __tablename__ = "reports"

    __table_args__ = (
        # One server report per local report: makes /reports/start idempotent.
        UniqueConstraint("user_id", "client_id", name="uq_reports_user_client"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    client_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    report_number: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus),
        default=ReportStatus.DRAFT,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    device_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    app_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    pdf_generated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    email_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    sync_status: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    user = relationship("User")