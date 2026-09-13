"""SSRF base-URL validation tests."""

from __future__ import annotations

import pytest
from app.ai.urlsafety import UnsafeBaseUrlError, validate_base_url
from app.core.config import get_settings


def _settings(**overrides):
    return get_settings().model_copy(update=overrides)


def test_allows_public_https() -> None:
    assert validate_base_url("https://93.184.216.34/v1", _settings()) == "https://93.184.216.34/v1"


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/v1",
        "https://127.0.0.1/v1",
        "https://10.0.0.5/v1",
        "https://192.168.1.10/v1",
        "https://169.254.169.254/latest/meta-data",
        "https://metadata.google.internal",
        "ftp://example.com",
    ],
)
def test_blocks_ssrf_targets(url: str) -> None:
    with pytest.raises(UnsafeBaseUrlError):
        validate_base_url(url, _settings())


def test_http_blocked_by_default_but_allowed_when_configured() -> None:
    with pytest.raises(UnsafeBaseUrlError):
        validate_base_url("http://example.com", _settings())
    assert validate_base_url("http://example.com", _settings(AI_ALLOW_HTTP_BASE_URL=True))


def test_private_allowed_when_explicitly_enabled() -> None:
    settings = _settings(AI_ALLOW_HTTP_BASE_URL=True, AI_ALLOW_PRIVATE_BASE_URL=True)
    assert validate_base_url("http://localhost:8080/v1", settings) == "http://localhost:8080/v1"
