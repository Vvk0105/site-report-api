from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy import or_

from app.models.report import Report
from app.enums.report import ReportStatus


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
    ):

        query = (
            select(Report)
            .order_by(
                Report.created_at.desc()
            )
        )

        if search:

            query = query.where(
                Report.report_number.ilike(
                    f"%{search}%"
                )
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

        return total, result.scalars().all()
    
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