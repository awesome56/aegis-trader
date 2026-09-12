"""Password hashing and JWT unit tests."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def _settings() -> Settings:
    return Settings(_env_file=None, JWT_SECRET="unit-test-secret-value-1234567890abcdef")


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_verify_password_handles_garbage_hash() -> None:
    assert verify_password("x", "not-a-bcrypt-hash") is False


def test_password_length_guard() -> None:
    with pytest.raises(ValueError):
        hash_password("a" * 100)


def test_access_token_roundtrip() -> None:
    settings = _settings()
    token = create_access_token("user-123", settings)
    payload = decode_token(token, expected_type="access", settings=settings)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["jti"]


def test_token_type_is_enforced() -> None:
    settings = _settings()
    refresh = create_refresh_token("user-123", settings)
    with pytest.raises(TokenError):
        decode_token(refresh, expected_type="access", settings=settings)


def test_tampered_token_is_rejected() -> None:
    settings = _settings()
    token = create_access_token("user-123", settings)
    with pytest.raises(TokenError):
        decode_token(token + "tampered", settings=settings)
