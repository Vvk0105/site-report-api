from sqlalchemy import select

from app.models.refresh_token import RefreshToken

from datetime import datetime
from datetime import timezone

class RefreshTokenRepository:

    def __init__(
        self,
        db,
    ):
        self.db = db

    async def create(
        self,
        token: RefreshToken,
    ):

        self.db.add(token)

    async def get(
        self,
        token: str,
    ):

        result = await self.db.execute(
            select(
                RefreshToken
            ).where(
                RefreshToken.token == token,
            )
        )

        return result.scalar_one_or_none()

    async def revoke(
        self,
        refresh_token: RefreshToken,
    ):

        refresh_token.revoked = True

        self.db.add(
            refresh_token,
        )

    async def revoke_all(
        self,
        user_id: int,
    ):

        result = await self.db.execute(
            select(
                RefreshToken
            ).where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,
            )
        )

        tokens = result.scalars().all()

        for token in tokens:

            token.revoked = True

            self.db.add(
                token,
            )

    async def get_valid(
        self,
        token: str,
    ):

        result = await self.db.execute(
            select(
                RefreshToken
            ).where(
                RefreshToken.token == token,
                RefreshToken.revoked == False,
            )
        )

        refresh = result.scalar_one_or_none()

        if not refresh:
            return None

        if refresh.expires_at < datetime.now(
            timezone.utc,
        ):
            return None

        return refresh
    
    async def revoke_token(
        self,
        token: str,
    ):

        refresh = await self.get(
            token,
        )

        if not refresh:
            return

        refresh.revoked = True

        self.db.add(
            refresh,
        )