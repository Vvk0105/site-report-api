from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.constants import REFRESH_TOKEN_EXPIRE_DAYS
from app.core.security import create_refresh_token, hash_refresh_token
from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    """
    Refresh tokens are stored as SHA-256 hashes in `RefreshToken.token`.
    The raw value is only ever returned to the client once, at issue time.
    """

    def __init__(self, db):
        self.db = db

    def issue(self, user_id: int) -> str:
        """Create a new refresh token for the user and return the raw value."""
        raw = create_refresh_token()

        self.db.add(
            RefreshToken(
                user_id=user_id,
                token=hash_refresh_token(raw),
                expires_at=datetime.now(timezone.utc)
                + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
                revoked=False,
            )
        )

        return raw

    async def get_for_update(self, raw_token: str) -> RefreshToken | None:
        """Load the token row with a row lock, so concurrent refreshes serialise."""
        result = await self.db.execute(
            select(RefreshToken)
            .where(RefreshToken.token == hash_refresh_token(raw_token))
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def revoke_all_for_user(self, user_id: int) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked.is_(False),
            )
            .values(revoked=True)
        )

    async def revoke(self, raw_token: str) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.token == hash_refresh_token(raw_token))
            .values(revoked=True)
        )
