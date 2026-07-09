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
from app.dependencies import get_current_user

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

@router.get("/me")
async def me(
    current_user=Depends(get_current_user),
):

    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
    }

from app.services.email_service import EmailService


@router.get("/test-email")
async def test_email():

    service = EmailService()

    await service.send_otp(
        "vivekbabu0105@gmail.com",
        "123456",
    )

    return {
        "message": "Email Sent"
    }