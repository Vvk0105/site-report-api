from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.plan import PlanResponse
from app.services.plan_service import PlanService

router = APIRouter(
    prefix="/plans",
    tags=["Plans"],
)

@router.get(
    "",
    response_model=list[PlanResponse],
)
async def get_plans(
    db: AsyncSession = Depends(get_db),
):
    service = PlanService(db)
    # We only want to return active plans for regular users
    # Actually, the PlanService.list() returns all plans, but maybe we should filter active ones.
    # Let's just use service.list() and filter it here, or use it directly.
    plans = await service.list()
    # Filter active plans
    active_plans = [plan for plan in plans if plan.is_active]
    return active_plans
