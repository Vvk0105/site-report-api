from app.core.security import (
    verify_password,
    create_access_token,
)
from datetime import datetime, timedelta, timezone

from app.models.refresh_token import RefreshToken
from app.repositories.refresh_token_repository import RefreshTokenRepository

from app.core.security import (
    create_access_token,
    create_refresh_token,
)

from app.core.constants import REFRESH_TOKEN_EXPIRE_DAYS

from fastapi import HTTPException

class AuthService:

    def __init__(self, repo):

        self.repo = repo
        self.refresh_repo = RefreshTokenRepository(repo.db)

    async def admin_login(
        self,
        email: str,
        password: str,
    ):

        
        user = await self.repo.get_by_email(email)

        if not user:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        access_token = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "is_admin": True,
            }
        )

        refresh_token = create_refresh_token()

        await self.refresh_repo.create(
            RefreshToken(
                user_id=user.id,
                token=refresh_token,
                expires_at=datetime.now(
                    timezone.utc,
                )
                + timedelta(
                    days=REFRESH_TOKEN_EXPIRE_DAYS,
                ),
            )
        )

        await self.repo.db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    
    async def refresh(
        self,
        refresh_token: str,
    ):

        token = await self.refresh_repo.get_valid(
            refresh_token,
        )

        if not token:
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
            )

        user = await self.repo.get_by_id(
            token.user_id,
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        token.revoked = True

        new_refresh = create_refresh_token()

        await self.refresh_repo.create(
            RefreshToken(
                user_id=user.id,
                token=new_refresh,
                expires_at=datetime.now(
                    timezone.utc,
                )
                + timedelta(
                    days=REFRESH_TOKEN_EXPIRE_DAYS,
                ),
            )
        )

        access = create_access_token(
            {
                "sub": str(user.id),
                "email": user.email,
                "is_admin": user.is_admin,
            }
        )

        await self.repo.db.commit()

        return {
            "access_token": access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }