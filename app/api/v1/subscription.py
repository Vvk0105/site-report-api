from fastapi import APIRouter
from fastapi import Depends

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.dependencies import get_current_user
from app.schemas.subscription import SubscriptionResponse
from app.services.subscription_service import SubscriptionService

router = APIRouter(
    prefix="/subscription",
    tags=["Subscription"],
)


@router.get(
    "",
    response_model=SubscriptionResponse,
)
async def get_subscription(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    service = SubscriptionService(db)

    return await service.get_subscription(
        current_user.id,
    )