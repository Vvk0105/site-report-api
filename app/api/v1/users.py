from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.dependencies import get_current_user
from app.repositories.user_repository import UserRepository

from app.schemas.user import UpdateProfileRequest

router = APIRouter()

@router.put("/me")
async def update_me(
    request: UpdateProfileRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    current_user.full_name = request.full_name
    repo.update(current_user)
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
    repo = UserRepository(db)
    await repo.delete(current_user)
    await db.commit()
    return {"message": "Profile deleted successfully"}
