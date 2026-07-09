from datetime import datetime, timezone

from app.enums.report import ReportStatus

from app.models.report import Report

from app.repositories.report_repository import ReportRepository

from app.services.subscription_service import SubscriptionService

from app.utils.report_number import generate_report_number
from fastapi import HTTPException

class ReportService:

    def __init__(self, db):

        self.db = db

        self.report_repo = ReportRepository(db)

        self.subscription_service = SubscriptionService(db)

    async def start_report(
        self,
        user_id: int,
        device_id: str | None,
        app_version: str | None,
    ):

        await self.subscription_service.validate_can_create_report(
            user_id
        )

        report = Report(
            user_id=user_id,
            status=ReportStatus.DRAFT,
            started_at=datetime.now(timezone.utc),
            device_id=device_id,
            app_version=app_version,
            report_number="TEMP",
        )

        self.report_repo.create(report)

        await self.db.flush()

        report.report_number = generate_report_number(
            report.id
        )

        await self.db.commit()

        await self.db.refresh(report)

        return {
            "report_id": report.id,
            "report_number": report.report_number,
            "status": report.status.value,
        }
    
    async def sync_report(
        self,
        report_id: int,
        user_id: int,
        data,
    ):

        report = await self.report_repo.get_by_id(
            report_id
        )

        if not report:

            raise HTTPException(
                404,
                "Report not found",
            )

        if report.user_id != user_id:

            raise HTTPException(
                403,
                "Permission denied",
            )

        report.pdf_generated = data.pdf_generated

        report.email_sent = data.email_sent

        report.sync_status = True

        report.status = ReportStatus.COMPLETED

        report.completed_at = datetime.now(
            timezone.utc
        )

        await self.db.commit()

        await self.db.refresh(report)

        return report
    
    async def history(
        self,
        user_id: int,
    ):

        return await self.report_repo.history(
            user_id
        )