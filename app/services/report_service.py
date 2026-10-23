from datetime import datetime, timezone

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.enums.report import ReportStatus
from app.models.report import Report
from app.repositories.report_repository import ReportRepository
from app.services.email_service import EmailService
from app.services.subscription_service import SubscriptionService
from app.utils.email import validate_email_address
from app.utils.report_number import generate_report_number

MAX_SUBJECT_LENGTH = 200
MAX_BODY_LENGTH = 10_000
PDF_MAGIC = b"%PDF"


class ReportService:

    def __init__(self, db):
        self.db = db
        self.report_repo = ReportRepository(db)
        self.subscription_service = SubscriptionService(db)
        self.email_service = EmailService()

    @staticmethod
    def _summary(report: Report) -> dict:
        return {
            "report_id": report.id,
            "report_number": report.report_number,
            "status": report.status.value,
        }

    async def start_report(
        self,
        user_id: int,
        device_id: str | None,
        app_version: str | None,
        client_id: str | None = None,
    ) -> dict:
        # Retries of the same local report return the existing server report and
        # do not consume another quota slot.
        if client_id:
            existing = await self.report_repo.get_by_client_id(user_id, client_id)
            if existing:
                return self._summary(existing)

        await self.subscription_service.validate_can_create_report(user_id)

        report = Report(
            user_id=user_id,
            client_id=client_id,
            status=ReportStatus.DRAFT,
            started_at=datetime.now(timezone.utc),
            device_id=device_id,
            app_version=app_version,
            report_number="TEMP",
        )
        self.report_repo.create(report)

        try:
            await self.db.flush()
        except IntegrityError:
            # Another request with the same client_id won the race.
            await self.db.rollback()
            existing = await self.report_repo.get_by_client_id(user_id, client_id)
            if existing:
                return self._summary(existing)
            raise

        report.report_number = generate_report_number(report.id)
        await self.db.commit()
        await self.db.refresh(report)

        return self._summary(report)

    async def sync_report(self, report_id: int, user_id: int, data):
        report = await self.get_report(report_id=report_id, user_id=user_id)

        # Progress only moves forward. A client can never clear a flag the server
        # already recorded (for example, after the report was emailed).
        report.pdf_generated = report.pdf_generated or data.pdf_generated
        report.email_sent = report.email_sent or data.email_sent
        report.sync_status = True
        report.status = ReportStatus.COMPLETED
        if report.completed_at is None:
            report.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(report)

        return report

    async def history(self, user_id: int):
        return await self.report_repo.history(user_id)

    async def get_report(self, report_id: int, user_id: int):
        report = await self.report_repo.get_by_id(report_id)

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if report.user_id != user_id:
            raise HTTPException(status_code=403, detail="Permission denied")

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
    ) -> dict:
        report = await self.get_report(report_id=report_id, user_id=user.id)

        to_email = validate_email_address(to_email, "recipient email")
        cc_email = validate_email_address(cc_email, "CC email") if cc_email else None

        subject = subject.strip()
        if not subject or len(subject) > MAX_SUBJECT_LENGTH:
            raise HTTPException(status_code=422, detail="Subject must be between 1 and 200 characters")

        if len(body) > MAX_BODY_LENGTH:
            raise HTTPException(status_code=422, detail="Message body is too long")

        # Read one byte past the limit so oversized uploads are rejected without loading them all.
        pdf_bytes = await pdf.read(settings.MAX_REPORT_PDF_BYTES + 1)
        if len(pdf_bytes) > settings.MAX_REPORT_PDF_BYTES:
            raise HTTPException(status_code=413, detail="PDF is too large")
        if not pdf_bytes.startswith(PDF_MAGIC):
            raise HTTPException(status_code=422, detail="Uploaded file is not a PDF")

        await self.email_service.send_report_pdf(
            pdf_bytes=pdf_bytes,
            filename=pdf.filename or f"{report.report_number}.pdf",
            to_email=to_email,
            cc_email=cc_email,
            subject=subject,
            body=body,
            inspector_name=user.full_name or user.email,
            inspector_email=user.email,
        )

        report.email_sent = True
        await self.db.commit()

        return {"message": "Email sent successfully"}
