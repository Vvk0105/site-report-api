import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

ACCESS_TOKEN_TYPE = "access"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed_password: str | None) -> bool:
    # Users created through OTP have no password, so there is nothing to check.
    if not hashed_password:
        return False
    return pwd_context.verify(password, hashed_password)


def create_access_token(data: dict) -> str:
    payload = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload.update({"exp": expire, "typ": ACCESS_TOKEN_TYPE})

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError:
        return None

    if payload.get("typ") != ACCESS_TOKEN_TYPE:
        return None

    return payload


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """Refresh tokens are stored hashed, so a leaked database cannot be replayed."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
