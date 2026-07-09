from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

from app.dependencies import get_current_user

from app.schemas.report import (
    StartReportRequest,
    StartReportResponse,
    SyncReportRequest,
    ReportResponse
)

from app.services.report_service import ReportService

router = APIRouter(
    prefix="/reports",
    tags=["Reports"],
)


@router.post(
    "/start",
    response_model=StartReportResponse,
)
async def start_report(
    request: StartReportRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    service = ReportService(db)

    return await service.start_report(
        user_id=current_user.id,
        device_id=request.device_id,
        app_version=request.app_version,
    )

@router.post(
    "/{report_id}/sync",
    response_model=ReportResponse,
)
async def sync_report(
    report_id: int,
    request: SyncReportRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    service = ReportService(db)

    return await service.sync_report(
        report_id=report_id,
        user_id=current_user.id,
        data=request,
    )

@router.get(
    "/history",
    response_model=list[ReportResponse],
)
async def history(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    service = ReportService(db)

    return await service.history(
        current_user.id,
    )