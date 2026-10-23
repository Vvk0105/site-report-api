from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.rate_limit import RateLimiter
from app.core.security import (
    ACCESS_TOKEN_TYPE,
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.enums.subscription import SubscriptionStatus
from app.models.report import Report
from app.schemas.admin import UpdateSubscriptionRequest
from app.schemas.plan import PlanCreateRequest

from app.services.stripe_service import to_minor_units
from app.utils.email import clean_header, normalize_email, validate_email_address
from app.utils.query import escape_like, safe_sort_column


# ─── money ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "amount, expected",
    [(19.99, 1999), (Decimal("19.99"), 1999), (0, 0), (10.10, 1010), (1.005, 101)],
)
def test_minor_units_do_not_truncate(amount, expected):
    assert to_minor_units(amount) == expected


# ─── tokens and passwords ────────────────────────────────────────────────

def test_access_token_round_trip_and_type_check():
    token = create_access_token({"sub": "7", "is_admin": False})
    assert decode_access_token(token)["sub"] == "7"


def test_token_without_access_type_is_rejected():
    from jose import jwt

    from app.core.config import settings

    forged = jwt.encode({"sub": "1", "exp": 4102444800}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    assert decode_access_token(forged) is None


def test_access_token_type_claim_is_set():
    from jose import jwt

    from app.core.config import settings

    token = create_access_token({"sub": "1"})
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert payload["typ"] == ACCESS_TOKEN_TYPE


def test_verify_password_handles_missing_hash():
    assert verify_password("anything", None) is False


def test_password_hash_round_trip():
    hashed = hash_password("correct horse")
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong", hashed)


def test_refresh_tokens_are_hashed_deterministically():
    assert hash_refresh_token("abc") == hash_refresh_token("abc")
    assert hash_refresh_token("abc") != "abc"
    assert len(hash_refresh_token("abc")) == 64


# ─── input normalisation and validation ──────────────────────────────────

def test_email_is_normalised():
    assert normalize_email("  Admin@Example.COM ") == "admin@example.com"


def test_invalid_email_is_rejected():
    with pytest.raises(HTTPException):
        validate_email_address("not-an-email")


def test_header_values_cannot_inject_lines():
    cleaned = clean_header("Hello\r\nBcc: victim@example.com")
    assert "\r" not in cleaned and "\n" not in cleaned


def test_like_wildcards_are_escaped():
    assert escape_like("50%_off") == "50\\%\\_off"


def test_unknown_sort_key_falls_back_to_default():
    column = safe_sort_column(Report, "password_hash", {"created_at"}, "created_at")
    assert column is Report.created_at


def test_plan_rejects_negative_price_and_bad_cycle():
    with pytest.raises(ValidationError):
        PlanCreateRequest(name="x", price=-1, billing_cycle="monthly", report_limit=3)
    with pytest.raises(ValidationError):
        PlanCreateRequest(name="x", price=1, billing_cycle="fortnightly", report_limit=3)


def test_plan_report_limit_below_unlimited_sentinel_is_rejected():
    with pytest.raises(ValidationError):
        PlanCreateRequest(name="x", price=1, billing_cycle="monthly", report_limit=-5)


def test_subscription_status_must_be_a_real_status():
    with pytest.raises(ValidationError):
        UpdateSubscriptionRequest(plan_id=1, status="trial")
    assert UpdateSubscriptionRequest(plan_id=1, status="cancelled").status == SubscriptionStatus.CANCELLED


# ─── rate limiting ───────────────────────────────────────────────────────

def test_rate_limiter_blocks_after_limit():
    limiter = RateLimiter(limit=2, window_seconds=60)
    limiter.check("k")
    limiter.check("k")
    with pytest.raises(HTTPException) as exc:
        limiter.check("k")
    assert exc.value.status_code == 429


def test_rate_limiter_is_per_key():
    limiter = RateLimiter(limit=1, window_seconds=60)
    limiter.check("a")
    limiter.check("b")


def test_rate_limiter_reset_clears_key():
    limiter = RateLimiter(limit=1, window_seconds=60)
    limiter.check("a")
    limiter.reset("a")
    limiter.check("a")
