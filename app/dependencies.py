from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.database import get_db
from app.repositories.user_repository import UserRepository

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    payload = decode_access_token(credentials.credentials)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await UserRepository(db).get_by_id(user_id)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Deactivated (or deleted) accounts must lose access immediately,
    # not when their token expires.
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    return user


async def get_current_admin(
    current_user=Depends(get_current_user),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    return current_user
