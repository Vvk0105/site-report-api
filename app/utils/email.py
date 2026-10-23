import re

from email.utils import formataddr

from fastapi import HTTPException

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_HEADER_UNSAFE = re.compile(r"[\r\n]+")


def normalize_email(email: str) -> str:
    """Emails are case-insensitive in practice; store and look them up in lowercase."""
    return email.strip().lower()


def validate_email_address(email: str, field: str = "email") -> str:
    cleaned = normalize_email(email)
    if not _EMAIL_RE.match(cleaned) or len(cleaned) > 254:
        raise HTTPException(status_code=422, detail=f"Invalid {field}: {email}")
    return cleaned


def clean_header(value: str) -> str:
    """Strip CR/LF so user input cannot inject extra mail headers."""
    return _HEADER_UNSAFE.sub(" ", value).strip()


def display_address(name: str, address: str) -> str:
    return formataddr((clean_header(name), address))
