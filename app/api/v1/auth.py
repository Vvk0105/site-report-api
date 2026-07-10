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

from app.repositories.otp_repository import OTPRepository
from app.repositories.login_log_repository import LoginLogRepository
from app.services.email_service import EmailService
from app.services.otp_service import OTPService
from app.schemas.auth import SendOTPRequest, VerifyOTPRequest

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

    response = await service.admin_login(
        request.email,
        request.password,
    )

    if not response:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    return response

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


@router.post("/send-otp")
async def send_otp(
    request: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
):

    service = OTPService(
        db=db,
        email_service=EmailService(),
    )

    return await service.send_otp(
        request.email,
    )

@router.post(
    "/verify-otp",
    response_model=LoginResponse,
)
async def verify_otp(
    request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):

    service = OTPService(
        db=db,
        email_service=EmailService(),
    )

    return await service.verify_otp(
        email=request.email,
        otp=request.otp,
    )