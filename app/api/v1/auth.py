from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import (
    admin_login_limiter,
    client_ip,
    otp_send_ip_limiter,
    otp_send_limiter,
    otp_verify_limiter,
)
from app.db.database import get_db
from app.dependencies import get_current_user
from app.schemas.auth import (
    AdminLoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshTokenRequest,
    SendOTPRequest,
    VerifyOTPRequest,
)
from app.services.auth_service import AuthService
from app.services.email_service import EmailService
from app.services.otp_service import OTPService
from app.utils.email import normalize_email

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/admin/login", response_model=LoginResponse)
async def admin_login(
    request: Request,
    body: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    email = normalize_email(body.email)
    admin_login_limiter.check(f"{client_ip(request)}:{email}")

    response = await AuthService(db).admin_login(email, body.password)

    if not response:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    admin_login_limiter.reset(f"{client_ip(request)}:{email}")
    return response


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
    }


@router.post("/send-otp")
async def send_otp(
    request: Request,
    body: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    email = normalize_email(body.email)
    otp_send_limiter.check(f"email:{email}")
    otp_send_ip_limiter.check(client_ip(request))

    return await OTPService(db=db, email_service=EmailService()).send_otp(email)


@router.post("/verify-otp", response_model=LoginResponse)
async def verify_otp(
    body: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    email = normalize_email(body.email)
    otp_verify_limiter.check(f"email:{email}")

    response = await OTPService(db=db, email_service=EmailService()).verify_otp(
        email=email,
        otp=body.otp,
    )

    otp_verify_limiter.reset(f"email:{email}")
    return response


@router.post("/refresh", response_model=LoginResponse)
async def refresh(
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).refresh(body.refresh_token)


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthService(db).logout(body.refresh_token)
