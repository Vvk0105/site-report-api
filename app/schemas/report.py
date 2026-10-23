from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StartReportRequest(BaseModel):
    device_id: str | None = Field(default=None, max_length=255)
    app_version: str | None = Field(default=None, max_length=20)
    # The app's local report id. Makes start retries safe.
    client_id: str | None = Field(default=None, max_length=64)


class StartReportResponse(BaseModel):
    report_id: int
    report_number: str
    status: str


class SyncReportRequest(BaseModel):
    pdf_generated: bool
    email_sent: bool


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_number: str
    status: str
    pdf_generated: bool
    email_sent: bool
    started_at: datetime
    completed_at: datetime | None
