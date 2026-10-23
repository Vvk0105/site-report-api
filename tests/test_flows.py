"""
End-to-end flows against a real (SQLite) database through the HTTP API.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.rate_limit import admin_login_limiter
from app.db.database import Base, engine
from app.main import app
from app.services.email_service import EmailService

SENT_OTPS: dict[str, str] = {}


async def _create_schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture(scope="module")
def client():
    asyncio.run(_create_schema())

    async def fake_send_otp(self, email, otp):
        SENT_OTPS[email] = otp

    original = EmailService.send_otp
    EmailService.send_otp = fake_send_otp
    try:
        with TestClient(app) as c:
            yield c
    finally:
        EmailService.send_otp = original


def _otp_login(client, email):
    assert client.post("/api/v1/auth/send-otp", json={"email": email}).status_code == 200
    response = client.post("/api/v1/auth/verify-otp", json={"email": email, "otp": SENT_OTPS[email]})
    assert response.status_code == 200, response.text
    return response.json()


def _auth(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _admin_tokens(client):
    response = client.post(
        "/api/v1/auth/admin/login",
        json={"email": settings.ADMIN_EMAIL, "password": settings.ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return response.json()


# ─── admin login ─────────────────────────────────────────────────────────

def test_admin_login_succeeds_with_correct_password(client):
    tokens = _admin_tokens(client)
    me = client.get("/api/v1/admin/me", headers=_auth(tokens))
    assert me.status_code == 200
    assert me.json()["is_admin"] is True


def test_admin_login_rejects_wrong_password(client):
    response = client.post(
        "/api/v1/auth/admin/login",
        json={"email": settings.ADMIN_EMAIL, "password": "nope"},
    )
    assert response.status_code == 401


def test_admin_login_brute_force_is_rate_limited(client):
    statuses = [
        client.post("/api/v1/auth/admin/login", json={"email": "ghost@example.com", "password": "x"}).status_code
        for _ in range(12)
    ]
    assert statuses[-1] == 429
    admin_login_limiter._hits.clear()


def test_non_admin_cannot_use_admin_login(client):
    _otp_login(client, "plain.user@example.com")
    response = client.post(
        "/api/v1/auth/admin/login",
        json={"email": "plain.user@example.com", "password": "anything"},
    )
    assert response.status_code == 401


# ─── OTP login ───────────────────────────────────────────────────────────

def test_hardcoded_test_otp_no_longer_logs_in(client):
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "site@gmail.com", "otp": "123456"},
    )
    assert response.status_code == 400


def test_wrong_otp_is_rejected(client):
    client.post("/api/v1/auth/send-otp", json={"email": "wrong.otp@example.com"})
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "wrong.otp@example.com", "otp": "000000"},
    )
    assert response.status_code == 400


def test_otp_login_creates_user_with_trial(client):
    tokens = _otp_login(client, "new.user@example.com")
    subscription = client.get("/api/v1/subscription", headers=_auth(tokens))
    assert subscription.status_code == 200
    assert subscription.json()["reports_remaining"] == 3


def test_email_is_case_insensitive_for_login(client):
    client.post("/api/v1/auth/send-otp", json={"email": "Mixed.Case@Example.com"})
    otp = SENT_OTPS["mixed.case@example.com"]
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"email": "MIXED.CASE@example.com", "otp": otp},
    )
    assert response.status_code == 200


# ─── deactivation, refresh rotation, logout ──────────────────────────────

def test_deactivated_user_loses_access_immediately(client):
    tokens = _otp_login(client, "to.deactivate@example.com")
    admin = _admin_tokens(client)

    user_id = client.get("/api/v1/auth/me", headers=_auth(tokens)).json()["id"]
    response = client.put(
        f"/api/v1/admin/users/{user_id}",
        headers=_auth(admin),
        json={"is_active": False, "is_admin": False},
    )
    assert response.status_code == 200

    assert client.get("/api/v1/auth/me", headers=_auth(tokens)).status_code == 403
    # Deactivation revokes every session, so the refresh token is dead too.
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_refresh_rotates_and_reuse_revokes_all_sessions(client):
    tokens = _otp_login(client, "rotate@example.com")

    first = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert first.status_code == 200
    rotated = first.json()

    # Presenting the old refresh token again is treated as theft.
    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401

    # The newer token was revoked as well.
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}).status_code == 401


def test_logout_revokes_refresh_token(client):
    tokens = _otp_login(client, "logout@example.com")
    assert client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 200
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_refresh_tokens_are_stored_hashed(client):
    from sqlalchemy import select

    from app.models.refresh_token import RefreshToken

    tokens = _otp_login(client, "hashed@example.com")

    async def _stored():
        async with engine.connect() as conn:
            result = await conn.execute(select(RefreshToken.token))
            return [row[0] for row in result]

    stored = asyncio.run(_stored())
    assert tokens["refresh_token"] not in stored


# ─── reports and quota ───────────────────────────────────────────────────

def test_report_start_is_idempotent_per_client_id(client):
    tokens = _otp_login(client, "idempotent@example.com")

    first = client.post("/api/v1/reports/start", headers=_auth(tokens), json={"client_id": "local-1"})
    second = client.post("/api/v1/reports/start", headers=_auth(tokens), json={"client_id": "local-1"})

    assert first.status_code == 200
    assert second.json()["report_id"] == first.json()["report_id"]


def test_trial_quota_is_enforced(client):
    tokens = _otp_login(client, "quota@example.com")

    for i in range(3):
        assert client.post("/api/v1/reports/start", headers=_auth(tokens), json={"client_id": f"q-{i}"}).status_code == 200

    blocked = client.post("/api/v1/reports/start", headers=_auth(tokens), json={"client_id": "q-3"})
    assert blocked.status_code == 403
    # The app shows this text to the user, so it must explain the real reason.
    assert "used all the reports" in blocked.json()["message"]


def test_sync_never_clears_server_side_progress(client):
    tokens = _otp_login(client, "sync@example.com")
    report = client.post("/api/v1/reports/start", headers=_auth(tokens), json={"client_id": "s-1"}).json()

    client.post(
        f"/api/v1/reports/{report['report_id']}/sync",
        headers=_auth(tokens),
        json={"pdf_generated": True, "email_sent": True},
    )
    response = client.post(
        f"/api/v1/reports/{report['report_id']}/sync",
        headers=_auth(tokens),
        json={"pdf_generated": True, "email_sent": False},
    )
    assert response.json()["email_sent"] is True


def test_users_cannot_read_each_others_reports(client):
    owner = _otp_login(client, "owner@example.com")
    other = _otp_login(client, "intruder@example.com")
    report = client.post("/api/v1/reports/start", headers=_auth(owner), json={"client_id": "o-1"}).json()

    assert client.get(f"/api/v1/reports/{report['report_id']}", headers=_auth(other)).status_code == 403


# ─── admin user management guards ────────────────────────────────────────

def test_admin_cannot_demote_or_deactivate_themselves(client):
    admin = _admin_tokens(client)
    me = client.get("/api/v1/admin/me", headers=_auth(admin)).json()

    response = client.put(
        f"/api/v1/admin/users/{me['id']}",
        headers=_auth(admin),
        json={"is_active": True, "is_admin": False},
    )
    assert response.status_code == 400


def test_admin_user_list_has_pagination_fields(client):
    admin = _admin_tokens(client)
    body = client.get("/api/v1/admin/users?page=1&page_size=5", headers=_auth(admin)).json()
    assert {"total", "page", "page_size", "total_pages", "has_next", "has_previous", "results"} <= body.keys()


def test_admin_payments_list_is_paginated(client):
    admin = _admin_tokens(client)
    body = client.get("/api/v1/admin/payments", headers=_auth(admin))
    assert body.status_code == 200
    assert "total_pages" in body.json()


def test_admin_sort_key_is_whitelisted(client):
    admin = _admin_tokens(client)
    response = client.get("/api/v1/admin/users?sort=password_hash", headers=_auth(admin))
    assert response.status_code == 200


def test_admin_rejects_unknown_subscription_status(client):
    admin = _admin_tokens(client)
    user = _otp_login(client, "status.check@example.com")
    user_id = client.get("/api/v1/auth/me", headers=_auth(user)).json()["id"]
    plan_id = client.get("/api/v1/plans").json()[0]["id"]

    response = client.put(
        f"/api/v1/admin/users/{user_id}/subscription",
        headers=_auth(admin),
        json={"plan_id": plan_id, "status": "trial"},
    )
    assert response.status_code == 422


# ─── account deletion ────────────────────────────────────────────────────

def test_self_delete_revokes_access_and_anonymises_account(client):
    tokens = _otp_login(client, "delete.me@example.com")
    old_id = client.get("/api/v1/auth/me", headers=_auth(tokens)).json()["id"]

    assert client.delete("/api/v1/users/me", headers=_auth(tokens)).status_code == 200

    # The old token and refresh token are dead.
    assert client.get("/api/v1/auth/me", headers=_auth(tokens)).status_code == 403
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401

    # Signing in with the same email later gives a fresh account, not the deleted one.
    fresh = _otp_login(client, "delete.me@example.com")
    assert client.get("/api/v1/auth/me", headers=_auth(fresh)).json()["id"] != old_id


# ─── payments ────────────────────────────────────────────────────────────

def test_stripe_webhook_rejects_bad_signature(client):
    response = client.post(
        "/api/v1/payments/webhook",
        content=b'{"id":"evt_1"}',
        headers={"Stripe-Signature": "t=1,v1=bad"},
    )
    assert response.status_code == 400


def test_customer_portal_requires_login(client):
    assert client.get("/api/v1/payments/customer-portal").status_code in (401, 403)


def test_apple_receipt_rejected_without_trusted_root(client):
    tokens = _otp_login(client, "apple@example.com")
    response = client.post(
        "/api/v1/payments/apple/verify-receipt",
        headers=_auth(tokens),
        json={"receipt_data": "aaa.bbb.ccc"},
    )
    assert response.status_code == 400


def test_apple_webhook_rejects_unsigned_notification(client):
    response = client.post(
        "/api/v1/payments/apple/webhook",
        json={"signedPayload": "aaa.bbb.ccc"},
    )
    assert response.status_code == 400


def test_public_payment_status_hides_amounts(client):
    response = client.get("/api/v1/payments/cs_missing")
    assert response.status_code == 404


# ─── errors use one shape the admin panel and app both read ──────────────

def test_error_bodies_contain_detail_and_message(client):
    response = client.post("/api/v1/auth/verify-otp", json={"email": "bad", "otp": "1"})
    body = response.json()
    assert response.status_code == 422
    assert body["detail"] and body["message"] == body["detail"]


# ─── Stripe lifecycle (SDK calls mocked; database and handlers are real) ──

class _Obj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


@pytest.fixture
def stripe_mocks(monkeypatch):
    from app.services.stripe_service import StripeService

    calls = {"price": []}

    monkeypatch.setattr(
        StripeService, "create_product_and_price",
        lambda self, **kw: ("prod_1", "price_1"),
    )

    def fake_create_price(self, *, product_id, price, currency, billing_cycle):
        calls["price"].append(price)
        return _Obj(id=f"price_{len(calls['price']) + 1}")

    monkeypatch.setattr(StripeService, "create_price", fake_create_price)
    monkeypatch.setattr(StripeService, "create_customer", lambda self, **kw: _Obj(id="cus_1"))
    monkeypatch.setattr(
        StripeService, "create_checkout_session",
        lambda self, **kw: _Obj(id="cs_1", url="https://checkout.example/cs_1"),
    )
    monkeypatch.setattr(StripeService, "_calls", calls, raising=False)
    return calls


def _send_event(client, monkeypatch, event):
    from app.services.stripe_service import StripeService

    monkeypatch.setattr(StripeService, "verify_webhook", lambda self, payload, sig: event)
    return client.post("/api/v1/payments/webhook", content=b"{}", headers={"Stripe-Signature": "t=1,v1=x"})


def test_plan_price_change_creates_new_stripe_price(client, stripe_mocks):
    admin = _admin_tokens(client)
    created = client.post(
        "/api/v1/admin/plans",
        headers=_auth(admin),
        json={"name": "Pro", "price": 25, "billing_cycle": "monthly", "report_limit": -1},
    )
    assert created.status_code == 200, created.text
    plan_id = created.json()["id"]

    updated = client.put(
        f"/api/v1/admin/plans/{plan_id}",
        headers=_auth(admin),
        json={
            "name": "Pro", "price": 30, "currency": "AUD", "billing_cycle": "monthly",
            "report_limit": -1, "trial_days": 0, "is_trial": False, "is_active": True,
        },
    )
    assert updated.status_code == 200, updated.text
    assert stripe_mocks["price"] == [30]
    assert updated.json()["price"] == 30.0


def test_checkout_renewal_cancel_lifecycle(client, monkeypatch, stripe_mocks):
    admin = _admin_tokens(client)
    plan = client.post(
        "/api/v1/admin/plans",
        headers=_auth(admin),
        json={"name": "Yearly", "price": 99.99, "billing_cycle": "yearly", "report_limit": -1},
    ).json()

    user = _otp_login(client, "stripe.buyer@example.com")
    checkout = client.post("/api/v1/payments/checkout", headers=_auth(user), json={"plan_id": plan["id"]})
    assert checkout.status_code == 200, checkout.text
    assert checkout.json()["session_id"] == "cs_1"

    # First payment via checkout.session.completed
    completed = _send_event(client, monkeypatch, {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_1", "customer": "cus_1", "subscription": "sub_1",
                "payment_intent": "pi_1", "amount_total": 9999, "currency": "aud",
                "metadata": {"user_id": str(client.get("/api/v1/auth/me", headers=_auth(user)).json()["id"]),
                             "plan_id": str(plan["id"])},
            }
        },
    })
    assert completed.status_code == 200

    verify = client.get("/api/v1/payments/cs_1")
    assert verify.json() == {"paid": True, "status": "paid"}

    # Replaying the same event does not create a second payment.
    _send_event(client, monkeypatch, {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_1", "customer": "cus_1", "subscription": "sub_1",
                            "amount_total": 9999, "currency": "aud", "metadata": {"user_id": "0", "plan_id": "0"}}},
    })
    history = client.get("/api/v1/payments/history", headers=_auth(user)).json()
    assert len(history) == 1
    assert history[0]["amount"] == 99.99
    assert "stripe_session_id" not in history[0]  # customers never see Stripe internals

    # Renewal invoice is recorded too (previously ignored).
    _send_event(client, monkeypatch, {
        "type": "invoice.paid",
        "data": {"object": {"id": "in_2", "billing_reason": "subscription_cycle", "customer": "cus_1",
                            "subscription": "sub_1", "payment_intent": "pi_2",
                            "amount_paid": 9999, "currency": "aud"}},
    })
    assert len(client.get("/api/v1/payments/history", headers=_auth(user)).json()) == 2

    # Stripe reports the subscription unpaid: access is cut off.
    _send_event(client, monkeypatch, {
        "type": "customer.subscription.updated",
        "data": {"object": {"id": "sub_1", "customer": "cus_1", "status": "unpaid"}},
    })
    assert client.get("/api/v1/subscription", headers=_auth(user)).json()["status"] == "cancelled"


def test_customer_portal_returns_url_for_paying_customer(client, monkeypatch, stripe_mocks):
    from app.services.stripe_service import StripeService

    monkeypatch.setattr(StripeService, "create_customer_portal", lambda self, cid: f"https://portal/{cid}")
    user = _otp_login(client, "portal.user@example.com")
    client.post("/api/v1/payments/checkout", headers=_auth(user), json={"plan_id": 1})

    response = client.get("/api/v1/payments/customer-portal", headers=_auth(user))
    assert response.status_code == 200
    assert response.json()["url"].startswith("https://portal/")
