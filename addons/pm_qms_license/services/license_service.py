import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .environment import read_environment_id


CANONICALIZATION = "UTF-8 JSON with sorted keys, compact separators, no ASCII escaping"
REQUIRED_PAYLOAD_FIELDS = {
    "schema_version",
    "license_id",
    "license_revision",
    "customer_name",
    "edition",
    "environment_id",
    "company_limit",
    "site_limit",
    "named_user_limit",
    "issued_at",
    "not_before",
    "expires_at",
    "perpetual",
    "key_id",
}


class LicenseValidationError(ValueError):
    pass


TEMPORAL_STATES = {"valid", "expiring", "expired", "not_yet_valid"}


def effective_temporal_state(stored_state, not_before, expires_at, perpetual, now=None):
    """Return the current term state without changing the signed license payload."""
    if stored_state not in TEMPORAL_STATES:
        return stored_state
    now = now or datetime.now(timezone.utc)
    if not_before and not_before.tzinfo is None:
        not_before = not_before.replace(tzinfo=timezone.utc)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if not_before and now < not_before:
        return "not_yet_valid"
    if perpetual:
        return "valid"
    if expires_at and now >= expires_at:
        return "expired"
    if expires_at and expires_at - now <= timedelta(days=30):
        return "expiring"
    return "valid"


def canonical_payload(payload):
    if not isinstance(payload, dict):
        raise LicenseValidationError("License payload must be an object.")
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def payload_fingerprint(payload):
    return hashlib.sha256(canonical_payload(payload)).hexdigest()


def _decode_b64(value, label):
    try:
        return base64.b64decode(value, validate=True)
    except (TypeError, ValueError) as exc:
        raise LicenseValidationError(f"Invalid {label} encoding.") from exc


def _parse_datetime(value, label):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise LicenseValidationError(f"Invalid {label} timestamp.") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def public_keys_path():
    return Path(__file__).resolve().parent.parent / "data" / "public_keys.json"


def load_public_keys(path=None):
    key_path = Path(path) if path else public_keys_path()
    try:
        data = json.loads(key_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise LicenseValidationError("Approved public-key registry is unavailable.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("keys"), dict):
        raise LicenseValidationError("Approved public-key registry has an invalid format.")
    return data["keys"]


def _public_key_from_b64(value):
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError as exc:
        raise LicenseValidationError("The Ed25519 cryptography provider is unavailable.") from exc
    raw = _decode_b64(value, "public key")
    if len(raw) != 32:
        raise LicenseValidationError("Ed25519 public key must contain 32 bytes.")
    return Ed25519PublicKey.from_public_bytes(raw), raw


def validate_document(document, expected_environment_id=None, public_keys=None, now=None):
    if isinstance(document, bytes):
        try:
            document = document.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise LicenseValidationError("License file must be UTF-8 JSON.") from exc
    if isinstance(document, str):
        try:
            document = json.loads(document)
        except json.JSONDecodeError as exc:
            raise LicenseValidationError("License file is not valid JSON.") from exc
    if not isinstance(document, dict) or not isinstance(document.get("payload"), dict):
        raise LicenseValidationError("License file must contain a payload object.")
    payload = document["payload"]
    missing = sorted(REQUIRED_PAYLOAD_FIELDS - set(payload))
    if missing:
        raise LicenseValidationError("License payload is missing required fields: " + ", ".join(missing))
    if payload.get("schema_version") != 1:
        raise LicenseValidationError("Unsupported license schema version.")
    if not isinstance(payload.get("license_revision"), int) or payload["license_revision"] < 1:
        raise LicenseValidationError("License revision must be a positive integer.")
    for field in ("company_limit", "site_limit", "named_user_limit"):
        if not isinstance(payload.get(field), int) or payload[field] < 1:
            raise LicenseValidationError(f"{field} must be a positive integer.")
    if not isinstance(payload.get("perpetual"), bool):
        raise LicenseValidationError("perpetual must be a boolean.")
    if payload["perpetual"] and payload.get("expires_at") is not None:
        raise LicenseValidationError("A perpetual license cannot have an expiry timestamp.")
    if not payload["perpetual"] and not payload.get("expires_at"):
        raise LicenseValidationError("A term license must have an expiry timestamp.")
    signature = _decode_b64(document.get("signature"), "signature")
    if len(signature) != 64:
        raise LicenseValidationError("Ed25519 signature must contain 64 bytes.")
    keys = public_keys if public_keys is not None else load_public_keys()
    key_value = keys.get(payload["key_id"])
    if not key_value:
        raise LicenseValidationError("License key_id is not approved.")
    public_key, public_key_bytes = _public_key_from_b64(key_value)
    try:
        public_key.verify(signature, canonical_payload(payload))
    except Exception as exc:
        raise LicenseValidationError("License signature is invalid.") from exc
    expected_environment_id = expected_environment_id or read_environment_id()
    if not expected_environment_id:
        raise LicenseValidationError("Perfect Match environment identity is not configured.")
    if payload["environment_id"] != expected_environment_id:
        raise LicenseValidationError("License belongs to a different Perfect Match environment.")
    now = now or datetime.now(timezone.utc)
    not_before = _parse_datetime(payload["not_before"], "not_before")
    expires_at = _parse_datetime(payload.get("expires_at"), "expires_at")
    issued_at = _parse_datetime(payload["issued_at"], "issued_at")
    state = effective_temporal_state(
        "valid",
        not_before,
        expires_at,
        payload["perpetual"],
        now=now,
    )
    return {
        "payload": payload,
        "signature": document["signature"],
        "state": state,
        "fingerprint": payload_fingerprint(payload),
        "public_key_fingerprint": hashlib.sha256(public_key_bytes).hexdigest(),
        "issued_at": issued_at,
        "not_before": not_before,
        "expires_at": expires_at,
    }


def sign_payload(payload, private_key_path):
    try:
        from cryptography.hazmat.primitives import serialization
    except ImportError as exc:
        raise LicenseValidationError("The Ed25519 cryptography provider is unavailable.") from exc
    try:
        private_bytes = Path(private_key_path).read_bytes()
        private_key = serialization.load_pem_private_key(private_bytes, password=None)
        signature = private_key.sign(canonical_payload(payload))
    except (OSError, ValueError, TypeError) as exc:
        raise LicenseValidationError("Unable to load the external signing key.") from exc
    return {
        "format": "pmqms-license",
        "format_version": 1,
        "payload": payload,
        "signature": base64.b64encode(signature).decode("ascii"),
    }


def issue_license(payload, private_key_path, output_path):
    document = sign_payload(payload, private_key_path)
    Path(output_path).write_text(json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return document
