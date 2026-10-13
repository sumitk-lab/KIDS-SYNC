"""Security utilities: Password hashing, JWT token handling, and cryptographic audit hashing."""

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from src.core.config import settings
from src.core.exceptions import AuthenticationError

# PBKDF2 Password Hashing parameters
PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a cryptographically secure random salt."""
    salt = secrets.token_bytes(SALT_BYTES)
    key = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    # Format: algorithm$iterations$salt_b64$key_b64
    salt_b64 = base64.b64encode(salt).decode("ascii")
    key_b64 = base64.b64encode(key).decode("ascii")
    return f"{PBKDF2_ALGORITHM}${PBKDF2_ITERATIONS}${salt_b64}${key_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored PBKDF2 hash."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 4:
            return False
        algorithm, iterations_str, salt_b64, key_b64 = parts
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_key = base64.b64decode(key_b64.encode("ascii"))

        computed_key = hashlib.pbkdf2_hmac(
            algorithm,
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(computed_key, expected_key)
    except Exception:
        return False


def create_access_token(subject: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: str) -> str:
    """Create a signed JWT refresh token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Authentication token has expired.")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid authentication token.")


def hash_client_ip(client_ip: Optional[str]) -> str:
    """Hash client IP using SHA-256 for anonymized COPPA/GDPR compliant audit logs."""
    raw = client_ip or "127.0.0.1"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_audit_entry_hash(
    prev_entry_hash: str,
    created_at_iso: str,
    actor_id: str,
    target_entity: str,
    entity_id: str,
    payload_snapshot: Dict[str, Any],
) -> str:
    """
    Compute cryptographic HMAC-SHA256 hash for court-admissible audit chaining:
    Hash_n = HMAC-SHA256(prev_hash || timestamp || actor_id || target_entity || entity_id || payload, key)
    """
    canonical_payload = json.dumps(payload_snapshot, sort_keys=True, default=str)
    raw_message = (
        f"{prev_entry_hash}|"
        f"{created_at_iso}|"
        f"{actor_id}|"
        f"{target_entity}|"
        f"{entity_id}|"
        f"{canonical_payload}"
    )
    key_bytes = settings.AUDIT_HMAC_MASTER_KEY.encode("utf-8")
    h = hmac.new(key_bytes, raw_message.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()
