from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.plan import PlanResponse
from app.services.plan_service import PlanService

router = APIRouter(
    prefix="/plans",
    tags=["Plans"],
)


@router.get("", response_model=list[PlanResponse])
async def get_plans(db: AsyncSession = Depends(get_db)):
    """Plans a customer can buy. Inactive plans are filtered in SQL."""
    return await PlanService(db).list_public()
