from fastapi import HTTPException

from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository


class AdminReportService:

    def __init__(self, db):

        self.db = db

        self.report_repo = ReportRepository(db)

        self.user_repo = UserRepository(db)

    async def list_reports(
        self,
        page,
        page_size,
        search,
    ):

        total, rows = await self.report_repo.admin_reports(
            page,
            page_size,
            search,
        )

        results = []

        for report, email in rows:

            results.append(
                {
                    "id": report.id,
                    "report_number": report.report_number,
                    "user_id": report.user_id,
                    "inspector_email": email,
                    "status": report.status.value,
                    "email_sent": report.email_sent,
                    "device_id": report.device_id,
                    "app_version": report.app_version,
                    "created_at": report.created_at,
                    "completed_at": report.completed_at,
                }
            )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": results,
        }

    async def get_report(
        self,
        report_id,
    ):

        report = await self.report_repo.get_by_id(
            report_id,
        )

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found",
            )

        user = await self.user_repo.get_by_id(
            report.user_id,
        )

        return {
            "id": report.id,
            "report_number": report.report_number,
            "user_id": report.user_id,
            "inspector_email": user.email,
            "status": report.status.value,
            "email_sent": report.email_sent,
            "device_id": report.device_id,
            "app_version": report.app_version,
            "created_at": report.created_at,
            "completed_at": report.completed_at,
        }

    async def delete_report(
        self,
        report_id,
    ):

        report = await self.report_repo.get_by_id(
            report_id
        )

        if not report:
            raise HTTPException(
                404,
                "Report not found",
            )

        await self.report_repo.delete(
            report
        )

        await self.db.commit()

        return {
            "message": "Report deleted successfully"
        }