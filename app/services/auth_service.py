from datetime import datetime, timezone

from fastapi import HTTPException

from app.core.security import create_access_token, verify_password
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository


class AuthService:

    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)

    def _tokens_for(self, user, refresh_token: str) -> dict:
        return {
            "access_token": create_access_token(
                {
                    "sub": str(user.id),
                    "email": user.email,
                    "is_admin": user.is_admin,
                }
            ),
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def admin_login(self, email: str, password: str) -> dict | None:
        user = await self.user_repo.get_by_email(email)

        # Same response for "unknown email", "wrong password", "not an admin"
        # and "deactivated", so the endpoint doesn't reveal which one it was.
        if (
            not user
            or not user.is_admin
            or not user.is_active
            or not verify_password(password, user.password_hash)
        ):
            return None

        refresh_token = self.refresh_repo.issue(user.id)
        await self.db.commit()

        return self._tokens_for(user, refresh_token)

    async def refresh(self, raw_refresh_token: str) -> dict:
        token = await self.refresh_repo.get_for_update(raw_refresh_token)

        if not token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        # A revoked token being presented again means it was copied or leaked.
        # Revoke every session for the user and make them sign in again.
        if token.revoked:
            await self.refresh_repo.revoke_all_for_user(token.user_id)
            await self.db.commit()
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Refresh token expired")

        user = await self.user_repo.get_by_id(token.user_id)

        if not user:
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        if not user.is_active:
            await self.refresh_repo.revoke_all_for_user(user.id)
            await self.db.commit()
            raise HTTPException(status_code=403, detail="Account is deactivated")

        token.revoked = True
        new_refresh_token = self.refresh_repo.issue(user.id)

        await self.db.commit()

        return self._tokens_for(user, new_refresh_token)

    async def logout(self, raw_refresh_token: str) -> dict:
        await self.refresh_repo.revoke(raw_refresh_token)
        await self.db.commit()

        return {"message": "Logged out successfully"}
