"""Password hashing and JWT token helpers.

Broker/LLM credentials must never reach the mobile client; only this backend
holds secrets. Token payloads intentionally contain no sensitive data.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import Settings, get_settings

TokenType = Literal["access", "refresh"]

# bcrypt has a hard 72-byte input limit; longer inputs are silently truncated by
# some implementations, so we reject them rather than accept ambiguous material.
_BCRYPT_MAX_BYTES = 72


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or validated."""


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    encoded = password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_BYTES:
        raise ValueError("Password exceeds the maximum supported length")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def _create_token(
    subject: str,
    token_type: TokenType,
    expires_delta: timedelta,
    settings: Settings,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    subject: str,
    settings: Settings | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = settings or get_settings()
    return _create_token(
        subject,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        settings,
        extra_claims,
    )


def create_refresh_token(
    subject: str,
    settings: Settings | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = settings or get_settings()
    return _create_token(
        subject,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        settings,
        extra_claims,
    )


def decode_token(
    token: str,
    expected_type: TokenType | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Decode and validate a JWT, optionally enforcing its token type."""
    settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.PyJWTError as exc:  # pragma: no cover - exercised via unit tests
        raise TokenError(str(exc)) from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise TokenError(f"Expected '{expected_type}' token")
    return payload
