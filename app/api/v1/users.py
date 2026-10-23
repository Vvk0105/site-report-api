from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.dependencies import get_current_user
from app.repositories.user_repository import UserRepository
from app.schemas.user import UpdateProfileRequest
from app.services.account_service import delete_stripe_customer, purge_personal_data

router = APIRouter()


@router.put("/me")
async def update_me(
    request: UpdateProfileRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.full_name = request.full_name
    UserRepository(db).update(current_user)
    await db.commit()
    await db.refresh(current_user)

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
    }


@router.delete("/me")
async def delete_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Permanently removes the caller's personal data (required for in-app account deletion)."""
    customer_id = current_user.stripe_customer_id

    await purge_personal_data(db, current_user)
    await db.commit()

    await delete_stripe_customer(customer_id)

    return {"message": "Account deleted successfully"}
