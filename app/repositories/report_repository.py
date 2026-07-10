from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import or_

from app.models.report import Report
from app.enums.report import ReportStatus
from app.models.user import User

from sqlalchemy import and_, asc, desc

class ReportRepository:

    def __init__(self, db):
        self.db = db

    def create(
        self,
        report: Report,
    ):
        self.db.add(report)

    async def get_by_id(
        self,
        report_id: int,
    ):

        result = await self.db.execute(
            select(Report).where(
                Report.id == report_id
            )
        )

        return result.scalar_one_or_none()

    async def completed_count(
        self,
        user_id: int,
    ):

        result = await self.db.execute(
            select(func.count(Report.id)).where(
                Report.user_id == user_id,
                Report.status == ReportStatus.COMPLETED,
            )
        )

        return result.scalar_one()
    
    async def history(
        self,
        user_id: int,
    ):

        result = await self.db.execute(
            select(Report)
            .where(
                Report.user_id == user_id
            )
            .order_by(
                Report.created_at.desc()
            )
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

        query = (
            select(
                Report,
                User.email.label("email"),
            )
            .join(
                User,
                User.id == Report.user_id,
            )
        )

        filters = []

        if search:

            filters.append(
                or_(
                    Report.report_number.ilike(
                        f"%{search}%"
                    ),
                    User.email.ilike(
                        f"%{search}%"
                    ),
                )
            )

        if status:

            filters.append(
                Report.status == status
            )

        if email_sent is not None:

            filters.append(
                Report.email_sent == email_sent
            )

        if date_from:

            filters.append(
                Report.created_at >= date_from
            )

        if date_to:

            filters.append(
                Report.created_at <= date_to
            )

        if filters:

            query = query.where(
                and_(*filters)
            )

        sort_column = getattr(
            Report,
            sort,
            Report.created_at,
        )

        query = query.order_by(
            asc(sort_column)
            if order == "asc"
            else desc(sort_column)
        )

        total = await self.db.scalar(
            select(func.count()).select_from(
                query.subquery()
            )
        )

        result = await self.db.execute(
            query.offset(
                (page - 1) * page_size
            ).limit(page_size)
        )

        return total, result.all()
    
    async def get_by_id(
        self,
        report_id: int,
    ):

        result = await self.db.execute(
            select(Report).where(
                Report.id == report_id
            )
        )

        return result.scalar_one_or_none()
    
    async def delete(
        self,
        report,
    ):

        await self.db.delete(
            report
        )