from datetime import datetime, timezone

from app.enums.report import ReportStatus

from app.models.report import Report

from app.repositories.report_repository import ReportRepository

from app.services.subscription_service import SubscriptionService

from app.utils.report_number import generate_report_number

from fastapi import UploadFile, HTTPException

from app.services.email_service import EmailService
class ReportService:

    def __init__(self, db):

        self.db = db

        self.report_repo = ReportRepository(db)

        self.subscription_service = SubscriptionService(db)

        self.email_service = EmailService()

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
    
    async def get_report(
        self,
        report_id: int,
        user_id: int,
    ):

        report = await self.report_repo.get_by_id(
            report_id
        )

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found",
            )

        if report.user_id != user_id:
            raise HTTPException(
                status_code=403,
                detail="Permission denied",
            )

        return report
    
    async def send_email(
        self,
        report_id: int,
        user,
        pdf: UploadFile,
        to_email: str,
        cc_email: str | None,
        subject: str,
        body: str,
    ):
        report = await self.report_repo.get_by_id(
            report_id
        )

        if not report:
            raise HTTPException(
                status_code=404,
                detail="Report not found",
            )

        if report.user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail="Permission denied",
            )

        await self.email_service.send_report_pdf(
            pdf=pdf,
            to_email=to_email,
            cc_email=cc_email,
            subject=subject,
            body=body,
            inspector_name=user.full_name or user.email,
            inspector_email=user.email,
        )

        report.email_sent = True

        await self.db.commit()

        return {
            "message": "Email sent successfully"
        }