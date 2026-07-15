from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.dependencies import get_current_admin

from app.schemas.plan import (
    PlanCreateRequest,
    PlanUpdateRequest,
    PlanResponse,
)

from app.services.plan_service import PlanService

router = APIRouter(
    prefix="/admin/plans",
    tags=["Admin Plans"],
)


@router.get(
    "",
    response_model=list[PlanResponse],
)
async def plans(
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await PlanService(
        db,
    ).list()


@router.post(
    "",
    response_model=PlanResponse,
)
async def create(
    request: PlanCreateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await PlanService(
        db,
    ).create(request)


@router.put(
    "/{plan_id}",
    response_model=PlanResponse,
)
async def update(
    plan_id: int,
    request: PlanUpdateRequest,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await PlanService(
        db,
    ).update(
        plan_id,
        request,
    )


@router.delete(
    "/{plan_id}",
)
async def delete(
    plan_id: int,
    admin=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):

    return await PlanService(
        db,
    ).delete(
        plan_id,
    )