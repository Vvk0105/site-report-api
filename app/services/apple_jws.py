"""
Verification for Apple StoreKit 2 / App Store Server Notification JWS tokens.

A token is only trusted when:
  * its ES256 signature matches the leaf certificate in the `x5c` header,
  * the certificate chain (leaf -> intermediate -> trusted Apple root) is valid, and
  * every certificate is inside its validity period.

The trusted root is loaded from APPLE_ROOT_CA_PATH (Apple Root CA - G3). Without it,
every Apple token is rejected: an unverified token must never grant a subscription.
"""

import base64
import json
from datetime import datetime, timezone
from functools import lru_cache

from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from app.core.config import settings


class AppleVerificationError(Exception):
    pass


def _b64url_decode(segment: str) -> bytes:
    return base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


@lru_cache(maxsize=1)
def _trusted_root() -> x509.Certificate:
    path = settings.APPLE_ROOT_CA_PATH
    if not path:
        raise AppleVerificationError("APPLE_ROOT_CA_PATH is not configured")

    with open(path, "rb") as handle:
        data = handle.read()

    try:
        return x509.load_pem_x509_certificate(data)
    except ValueError:
        return x509.load_der_x509_certificate(data)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _verify_issued_by(cert: x509.Certificate, issuer: x509.Certificate) -> None:
    if cert.issuer != issuer.subject:
        raise AppleVerificationError("Certificate issuer mismatch")
    try:
        issuer.public_key().verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            ec.ECDSA(cert.signature_hash_algorithm),
        )
    except InvalidSignature as exc:
        raise AppleVerificationError("Certificate chain signature invalid") from exc


def _verify_es256(parts: list[str], public_key) -> None:
    signature = _b64url_decode(parts[2])
    if len(signature) != 64:
        raise AppleVerificationError("Malformed ES256 signature")

    der_signature = encode_dss_signature(
        int.from_bytes(signature[:32], "big"),
        int.from_bytes(signature[32:], "big"),
    )
    try:
        public_key.verify(
            der_signature,
            f"{parts[0]}.{parts[1]}".encode("ascii"),
            ec.ECDSA(hashes.SHA256()),
        )
    except InvalidSignature as exc:
        raise AppleVerificationError("JWS signature invalid") from exc


def verify_jws(token: str) -> dict:
    """Return the decoded payload of a verified Apple JWS, or raise AppleVerificationError."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise AppleVerificationError("Not a JWS token")

    try:
        header = json.loads(_b64url_decode(parts[0]))
        x5c = header.get("x5c") or []
        if header.get("alg") != "ES256" or len(x5c) < 2:
            raise AppleVerificationError("Unsupported JWS header")

        leaf = x509.load_der_x509_certificate(base64.b64decode(x5c[0]))
        intermediate = x509.load_der_x509_certificate(base64.b64decode(x5c[1]))
        payload = json.loads(_b64url_decode(parts[1]))
    except AppleVerificationError:
        raise
    except Exception as exc:
        raise AppleVerificationError("Malformed JWS token") from exc

    root = _trusted_root()

    now = datetime.now(timezone.utc)
    for cert in (leaf, intermediate):
        if not (_utc(cert.not_valid_before_utc if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before)
                <= now
                <= _utc(cert.not_valid_after_utc if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after)):
            raise AppleVerificationError("Certificate outside its validity period")

    _verify_issued_by(intermediate, root)
    _verify_issued_by(leaf, intermediate)
    _verify_es256(parts, leaf.public_key())

    if settings.APPLE_BUNDLE_ID and payload.get("bundleId") != settings.APPLE_BUNDLE_ID:
        raise AppleVerificationError("Token is for a different app")

    return payload
