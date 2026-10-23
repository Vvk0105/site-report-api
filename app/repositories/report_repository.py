from sqlalchemy import and_, func, or_, select

from app.models.report import Report
from app.models.user import User
from app.utils.query import apply_order, escape_like, safe_sort_column

REPORT_SORT_COLUMNS = {"id", "report_number", "status", "email_sent", "created_at", "completed_at"}


class ReportRepository:

    def __init__(self, db):
        self.db = db

    def create(self, report: Report) -> None:
        self.db.add(report)

    async def get_by_id(self, report_id: int) -> Report | None:
        result = await self.db.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()

    async def get_by_client_id(self, user_id: int, client_id: str) -> Report | None:
        result = await self.db.execute(
            select(Report).where(
                Report.user_id == user_id,
                Report.client_id == client_id,
            )
        )
        return result.scalar_one_or_none()

    async def count_for_user(self, user_id: int) -> int:
        """Every report a user has started, drafts included. This is what the quota counts."""
        result = await self.db.execute(
            select(func.count(Report.id)).where(Report.user_id == user_id)
        )
        return result.scalar_one()

    async def history(self, user_id: int):
        result = await self.db.execute(
            select(Report)
            .where(Report.user_id == user_id)
            .order_by(Report.created_at.desc())
        )
        return result.scalars().all()

    async def admin_reports(
        self,
        page: int,
        page_size: int,
        search: str | None,
        status: str | None = None,
        email_sent: bool | None = None,
        date_from=None,
        date_to=None,
        sort: str = "created_at",
        order: str = "desc",
    ):
        query = select(Report, User.email.label("email")).join(
            User, User.id == Report.user_id
        )

        filters = []

        if search:
            pattern = f"%{escape_like(search)}%"
            filters.append(
                or_(
                    Report.report_number.ilike(pattern, escape="\\"),
                    User.email.ilike(pattern, escape="\\"),
                )
            )

        if status:
            filters.append(Report.status == status)

        if email_sent is not None:
            filters.append(Report.email_sent == email_sent)

        if date_from:
            filters.append(Report.created_at >= date_from)

        if date_to:
            filters.append(Report.created_at <= date_to)

        if filters:
            query = query.where(and_(*filters))

        sort_column = safe_sort_column(Report, sort, REPORT_SORT_COLUMNS, "created_at")
        query = apply_order(query, sort_column, order)

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))

        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )

        return total, result.all()

    async def delete(self, report: Report) -> None:
        await self.db.delete(report)
