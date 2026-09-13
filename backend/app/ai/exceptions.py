"""Normalized provider errors.

Provider-specific exception payloads must never leak to clients; services catch
these and surface a safe, categorized message.
"""

from __future__ import annotations


class LLMProviderError(Exception):
    code = "provider_error"
    retryable = False

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ProviderAuthError(LLMProviderError):
    code = "provider_auth_error"


class ProviderModelError(LLMProviderError):
    code = "provider_model_error"


class ProviderRateLimitError(LLMProviderError):
    code = "provider_rate_limit"
    retryable = True


class ProviderUnavailableError(LLMProviderError):
    code = "provider_unavailable"
    retryable = True


class ProviderTimeoutError(LLMProviderError):
    code = "provider_timeout"
    retryable = True


class ProviderResponseError(LLMProviderError):
    code = "provider_response_error"
