"""OpenAI-compatible provider classification + gateway header tests."""

from __future__ import annotations

from app.ai.exceptions import ProviderModelError
from app.ai.providers.openai_compatible import OpenAICompatibleProvider, _classify
from app.core.config import get_settings


def test_unsupported_model_classified_as_model_error() -> None:
    body = '{"type":"error","error":{"type":"ModelError","message":"Model Foo is not supported"}}'
    assert isinstance(_classify(401, body), ProviderModelError)


def test_plain_401_is_auth_error() -> None:
    from app.ai.exceptions import ProviderAuthError

    assert isinstance(_classify(401, "unauthorized"), ProviderAuthError)


def test_opencode_gateway_gets_session_header() -> None:
    provider = OpenAICompatibleProvider(
        api_key="k",
        model="deepseek-v4.1-flash",
        base_url="https://opencode.ai/zen/go/v1",
        settings=get_settings(),
    )
    assert provider._headers()["x-opencode-session"]

    standard = OpenAICompatibleProvider(
        api_key="k",
        model="gpt-4o-mini",
        base_url="https://api.openai.com/v1",
        settings=get_settings(),
    )
    assert "x-opencode-session" not in standard._headers()
