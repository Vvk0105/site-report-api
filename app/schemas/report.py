from datetime import datetime

from pydantic import BaseModel


class StartReportRequest(BaseModel):
    device_id: str | None = None
    app_version: str | None = None


class StartReportResponse(BaseModel):
    report_id: int
    report_number: str
    status: str

class SyncReportRequest(BaseModel):
    pdf_generated: bool
    email_sent: bool


class ReportResponse(BaseModel):

    id: int

    report_number: str

    status: str

    pdf_generated: bool

    email_sent: bool

    started_at: datetime

    completed_at: datetime | None

    class Config:
        from_attributes = True