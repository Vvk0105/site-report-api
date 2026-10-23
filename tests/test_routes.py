from fastapi.testclient import TestClient

from app.api.v1.payment import router as payment_router
from app.main import app


def _paths_in_order(router):
    return [route.path for route in router.routes]


def test_customer_portal_is_declared_before_session_catch_all():
    paths = _paths_in_order(payment_router)
    assert paths.index("/payments/customer-portal") < paths.index("/payments/{session_id}")


def test_placeholder_routes_are_gone():
    paths = {getattr(r, "path", "") for r in app.routes}
    assert "/api/v1/stripe" not in paths
    assert "/api/v1/dashboard" not in paths


def test_protected_routes_require_a_token():
    client = TestClient(app)
    assert client.get("/api/v1/auth/me").status_code in (401, 403)
    assert client.get("/api/v1/admin/users").status_code in (401, 403)
    assert client.get("/api/v1/reports/history").status_code in (401, 403)
    assert client.get("/api/v1/payments/history").status_code in (401, 403)
