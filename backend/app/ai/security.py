"""Credential encryption for AI provider API keys.

Uses Fernet (AES-128-CBC + HMAC-SHA256, authenticated) with a key supplied by
``AI_CREDENTIAL_ENCRYPTION_KEY`` (urlsafe base64 32-byte key). Tokens are never
logged, never returned to clients and never placed in events.
"""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings, get_settings


class CredentialError(Exception):
    """Raised when credentials cannot be encrypted/decrypted safely."""


def generate_key() -> str:
    """Generate a new urlsafe base64 Fernet key (for operator bootstrapping)."""
    return Fernet.generate_key().decode("utf-8")


class CredentialCipher:
    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode("utf-8"))
        except (ValueError, TypeError) as exc:
            raise CredentialError(
                "AI_CREDENTIAL_ENCRYPTION_KEY is missing or invalid"
            ) from exc

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            raise CredentialError("cannot encrypt an empty credential")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError, TypeError) as exc:
            raise CredentialError("stored credential could not be decrypted") from exc


def get_cipher(settings: Settings | None = None) -> CredentialCipher:
    settings = settings or get_settings()
    if not settings.AI_CREDENTIAL_ENCRYPTION_KEY:
        raise CredentialError(
            "AI_CREDENTIAL_ENCRYPTION_KEY is not configured; cannot store provider credentials"
        )
    return CredentialCipher(settings.AI_CREDENTIAL_ENCRYPTION_KEY)


def mask_key(raw: str | None) -> str | None:
    if not raw:
        return None
    suffix = raw[-4:] if len(raw) >= 4 else raw
    return f"••••••{suffix}"
