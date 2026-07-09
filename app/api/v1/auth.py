from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db

from app.schemas.auth import (
    AdminLoginRequest,
    LoginResponse,
)

from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/admin/login",
    response_model=LoginResponse,
)
async def admin_login(
    request: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):

    repo = UserRepository(db)

    service = AuthService(repo)

    token = await service.admin_login(
        request.email,
        request.password,
    )

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    return LoginResponse(
        access_token=token,
    )