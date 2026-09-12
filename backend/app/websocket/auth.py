"""WebSocket authentication.

The browser cannot set an ``Authorization`` header on a WebSocket handshake, so
clients pass a short-lived **access token** as a query parameter (or a Bearer
header, for non-browser clients). Only the signed token is validated here; the
token is short-lived (``ACCESS_TOKEN_EXPIRE_MINUTES``) and no long-lived secret
is placed in the URL.
"""

from __future__ import annotations

import uuid

from app.core.config import Settings, get_settings
from app.core.security import TokenError, decode_token


def authenticate_ws_token(token: str | None, settings: Settings | None = None) -> uuid.UUID | None:
    if not token:
        return None
    try:
        payload = decode_token(token, expected_type="access", settings=settings or get_settings())
        return uuid.UUID(payload["sub"])
    except (TokenError, ValueError, TypeError, KeyError):
        return None
