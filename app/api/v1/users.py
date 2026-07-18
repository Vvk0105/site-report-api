from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.dependencies import get_current_user
from app.repositories.user_repository import UserRepository

router = APIRouter()

@router.delete("/me")
async def delete_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    await repo.delete(current_user)
    await db.commit()
    return {"message": "Profile deleted successfully"}
