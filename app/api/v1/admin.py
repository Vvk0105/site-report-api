from fastapi import APIRouter
from app.dependencies import get_current_admin
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

from app.schemas.admin import DashboardResponse

from app.services.dashboard_service import DashboardService

from fastapi import Query

from app.schemas.admin import (
    AdminUserListResponse,
    CreateUserRequest,
    AdminUserResponse,
    AdminUserDetailResponse,
    UpdateUserRequest,
    UpdateSubscriptionRequest,
    AdminSubscriptionResponse,
    AdminReportListResponse,
    AdminReportResponse,

)

from app.services.admin_user_service import (
    AdminUserService,
)


from app.services.subscription_service import (
    SubscriptionService,
)

from app.services.admin_report_service import (
    AdminReportService,
)

router = APIRouter(
    prefix='/admin',
    tags=["Admin"],
)

@router.get("/me")
async def admin_me(
    admin=Depends(get_current_admin)
):
    return {
        "id": admin.id,
        "email": admin.email,
        "name": admin.full_name,
        "is_admin": admin.is_admin,
    }

@router.get(
    "/dashboard",
    response_model=DashboardResponse,
)
async def dashboard(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    service = DashboardService(db)

    return await service.dashboard()

@router.get(
    "/users",
    response_model=AdminUserListResponse,
)
async def users(
    page: int = Query(1),
    page_size: int = Query(20),
    search: str | None = None,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await AdminUserService(
        db
    ).list_users(
        page,
        page_size,
        search,
    )


@router.post(
    "/users",
    response_model=AdminUserResponse,
)
async def create_user(
    request: CreateUserRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await AdminUserService(
        db
    ).create_user(
        request.email,
        request.full_name,
    )

@router.get(
    "/users/{user_id}",
    response_model=AdminUserDetailResponse,
)
async def get_user(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await AdminUserService(
        db,
    ).get_user(
        user_id,
    )

@router.put(
    "/users/{user_id}",
    response_model=AdminUserResponse,
)
async def update_user(
    user_id: int,
    request: UpdateUserRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await AdminUserService(
        db,
    ).update_user(
        user_id=user_id,
        full_name=request.full_name,
        is_active=request.is_active,
        is_admin=request.is_admin,
    )

@router.delete(
    "/users/{user_id}",
)
async def delete_user(
    user_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await AdminUserService(
        db,
    ).delete_user(
        user_id,
    )

@router.get(
    "/subscriptions",
    response_model=list[
        AdminSubscriptionResponse
    ],
)
async def subscriptions(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await SubscriptionService(
        db,
    ).admin_list()

@router.put(
    "/users/{user_id}/subscription",
    response_model=AdminSubscriptionResponse,
)
async def update_subscription(
    user_id: int,
    request: UpdateSubscriptionRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await SubscriptionService(
        db,
    ).admin_update(
        user_id=user_id,
        plan_type=request.plan_type,
        report_limit=request.report_limit,
        status=request.status,
        end_date=request.end_date,
    )

@router.get(
    "/reports",
    response_model=AdminReportListResponse,
)
async def reports(
    page: int = Query(1),
    page_size: int = Query(20),
    search: str | None = None,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await AdminReportService(
        db,
    ).list_reports(
        page,
        page_size,
        search,
    )

@router.get(
    "/reports/{report_id}",
    response_model=AdminReportResponse,
)
async def report(
    report_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await AdminReportService(
        db,
    ).get_report(
        report_id,
    )

@router.delete(
    "/reports/{report_id}",
)
async def delete_report(
    report_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await AdminReportService(
        db,
    ).delete_report(
        report_id,
    )