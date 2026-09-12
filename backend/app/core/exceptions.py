"""Domain exception hierarchy.

These are framework-agnostic. The API layer maps them to HTTP responses in
``app.api.errors``.
"""

from __future__ import annotations

from typing import Any


class AegisError(Exception):
    """Base class for all domain errors."""

    status_code: int = 400
    code: str = "aegis_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotFoundError(AegisError):
    status_code = 404
    code = "not_found"


class ConflictError(AegisError):
    status_code = 409
    code = "conflict"


class ValidationError(AegisError):
    status_code = 422
    code = "validation_error"


class AuthenticationError(AegisError):
    status_code = 401
    code = "authentication_error"


class AuthorizationError(AegisError):
    status_code = 403
    code = "authorization_error"


class LiveTradingRefusedError(AegisError):
    status_code = 403
    code = "live_trading_refused"


class RiskRejectedError(AegisError):
    status_code = 422
    code = "risk_rejected"


class TradingHaltedError(AegisError):
    status_code = 423
    code = "trading_halted"
