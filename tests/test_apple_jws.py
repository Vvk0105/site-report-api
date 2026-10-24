import base64
import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.x509.oid import NameOID

from app.core.config import settings
from app.services import apple_jws
from app.services.apple_jws import AppleVerificationError, verify_jws


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _make_cert(subject_cn, issuer_cn, subject_key, issuer_key, *, is_ca, not_before=None, not_after=None):
    now = datetime.now(timezone.utc)
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject_cn)]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_cn)]))
        .public_key(subject_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before or now - timedelta(days=1))
        .not_valid_after(not_after or now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=is_ca, path_length=None), critical=True)
    )
    return builder.sign(issuer_key, hashes.SHA256())


@pytest.fixture
def chain(tmp_path, monkeypatch):
    root_key = ec.generate_private_key(ec.SECP256R1())
    inter_key = ec.generate_private_key(ec.SECP256R1())
    leaf_key = ec.generate_private_key(ec.SECP256R1())

    root = _make_cert("Test Root", "Test Root", root_key, root_key, is_ca=True)
    inter = _make_cert("Test Inter", "Test Root", inter_key, root_key, is_ca=True)
    leaf = _make_cert("Test Leaf", "Test Inter", leaf_key, inter_key, is_ca=False)

    root_path = tmp_path / "root.pem"
    root_path.write_bytes(root.public_bytes(serialization.Encoding.PEM))

    monkeypatch.setattr(settings, "APPLE_ROOT_CA_PATH", str(root_path))
    monkeypatch.setattr(settings, "APPLE_BUNDLE_ID", "au.com.sitesreports.app")
    apple_jws._trusted_root.cache_clear()

    yield {
        "leaf_key": leaf_key,
        "leaf": leaf,
        "inter": inter,
        "inter_key": inter_key,
        "other_root_key": ec.generate_private_key(ec.SECP256R1()),
    }

    apple_jws._trusted_root.cache_clear()


def _sign(chain_data, payload: dict, leaf_key=None, leaf=None, inter=None) -> str:
    leaf = leaf or chain_data["leaf"]
    inter = inter or chain_data["inter"]
    leaf_key = leaf_key or chain_data["leaf_key"]

    header = {
        "alg": "ES256",
        "x5c": [
            base64.b64encode(leaf.public_bytes(serialization.Encoding.DER)).decode(),
            base64.b64encode(inter.public_bytes(serialization.Encoding.DER)).decode(),
        ],
    }
    signing_input = f"{_b64url(json.dumps(header).encode())}.{_b64url(json.dumps(payload).encode())}"
    der = leaf_key.sign(signing_input.encode(), ec.ECDSA(hashes.SHA256()))


    r, s = decode_dss_signature(der)
    signature = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return f"{signing_input}.{_b64url(signature)}"


def test_valid_token_is_accepted(chain):
    token = _sign(chain, {"bundleId": "au.com.sitesreports.app", "productId": "pro"})
    assert verify_jws(token)["productId"] == "pro"


def test_tampered_payload_is_rejected(chain):
    token = _sign(chain, {"bundleId": "au.com.sitesreports.app", "productId": "pro"})
    head, _, sig = token.split(".")
    forged = _b64url(json.dumps({"bundleId": "au.com.sitesreports.app", "productId": "free-for-all"}).encode())
    with pytest.raises(AppleVerificationError):
        verify_jws(f"{head}.{forged}.{sig}")


def test_unsigned_token_is_rejected(chain):
    header = _b64url(json.dumps({"alg": "none"}).encode())
    body = _b64url(json.dumps({"productId": "pro"}).encode())
    with pytest.raises(AppleVerificationError):
        verify_jws(f"{header}.{body}.")


def test_chain_not_anchored_to_trusted_root_is_rejected(chain, tmp_path, monkeypatch):
    other_root = _make_cert("Other Root", "Other Root", chain["other_root_key"], chain["other_root_key"], is_ca=True)
    other_path = tmp_path / "other.pem"
    other_path.write_bytes(other_root.public_bytes(serialization.Encoding.PEM))
    monkeypatch.setattr(settings, "APPLE_ROOT_CA_PATH", str(other_path))
    apple_jws._trusted_root.cache_clear()

    token = _sign(chain, {"bundleId": "au.com.sitesreports.app"})
    with pytest.raises(AppleVerificationError):
        verify_jws(token)


def test_expired_certificate_is_rejected(chain):
    now = datetime.now(timezone.utc)
    expired_leaf = _make_cert(
        "Test Leaf", "Test Inter", chain["leaf_key"], chain["inter_key"],
        is_ca=False,
        not_before=now - timedelta(days=10),
        not_after=now - timedelta(days=1),
    )
    token = _sign(chain, {"bundleId": "au.com.sitesreports.app"}, leaf=expired_leaf)
    with pytest.raises(AppleVerificationError):
        verify_jws(token)


def test_wrong_bundle_is_rejected(chain):
    token = _sign(chain, {"bundleId": "com.someone.else", "productId": "pro"})
    with pytest.raises(AppleVerificationError):
        verify_jws(token)


def test_missing_root_configuration_fails_closed(chain, monkeypatch):
    monkeypatch.setattr(settings, "APPLE_ROOT_CA_PATH", "")
    apple_jws._trusted_root.cache_clear()
    token = _sign(chain, {"bundleId": "au.com.sitesreports.app"})
    with pytest.raises(AppleVerificationError, match="not configured"):
        verify_jws(token)


def test_root_certificate_in_der_form_is_accepted(chain, tmp_path, monkeypatch):
    # Apple distributes AppleRootCA-G3.cer in DER form; it must work without conversion.
    root_pem = open(settings.APPLE_ROOT_CA_PATH, "rb").read()
    root = x509.load_pem_x509_certificate(root_pem)
    der_path = tmp_path / "AppleRootCA-G3.cer"
    der_path.write_bytes(root.public_bytes(serialization.Encoding.DER))

    monkeypatch.setattr(settings, "APPLE_ROOT_CA_PATH", str(der_path))
    apple_jws._trusted_root.cache_clear()

    token = _sign(chain, {"bundleId": "au.com.sitesreports.app", "productId": "pro"})
    assert verify_jws(token)["productId"] == "pro"


def test_notification_with_nested_bundle_id_is_accepted(chain):
    # App Store Server Notifications keep the bundle id under "data", not at the top level.
    token = _sign(chain, {
        "notificationType": "DID_RENEW",
        "data": {"bundleId": "au.com.sitesreports.app", "environment": "Sandbox"},
    })
    assert verify_jws(token)["notificationType"] == "DID_RENEW"


def test_notification_for_another_app_is_rejected(chain):
    token = _sign(chain, {
        "notificationType": "DID_RENEW",
        "data": {"bundleId": "com.someone.else"},
    })
    with pytest.raises(AppleVerificationError):
        verify_jws(token)


def test_notification_without_any_bundle_id_is_rejected(chain):
    token = _sign(chain, {"notificationType": "DID_RENEW", "data": {}})
    with pytest.raises(AppleVerificationError):
        verify_jws(token)
