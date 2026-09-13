"""Credential encryption + masking tests."""

from __future__ import annotations

import pytest
from app.ai.security import CredentialCipher, CredentialError, generate_key, get_cipher, mask_key
from app.core.config import get_settings


def test_encrypt_decrypt_round_trip() -> None:
    cipher = CredentialCipher(generate_key())
    token = cipher.encrypt("sk-secret-value")
    assert token != "sk-secret-value"
    assert cipher.decrypt(token) == "sk-secret-value"


def test_wrong_key_cannot_decrypt() -> None:
    token = CredentialCipher(generate_key()).encrypt("sk-secret")
    other = CredentialCipher(generate_key())
    with pytest.raises(CredentialError):
        other.decrypt(token)


def test_invalid_key_rejected() -> None:
    with pytest.raises(CredentialError):
        CredentialCipher("not-a-valid-key")


def test_get_cipher_requires_key() -> None:
    settings = get_settings().model_copy(update={"AI_CREDENTIAL_ENCRYPTION_KEY": ""})
    with pytest.raises(CredentialError):
        get_cipher(settings)


def test_mask_key() -> None:
    assert mask_key("sk-abcdef1234") == "••••••1234"
    assert mask_key("ab") == "••••••ab"
    assert mask_key(None) is None
