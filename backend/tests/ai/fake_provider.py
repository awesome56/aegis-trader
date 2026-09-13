"""Deterministic fake LLM provider for tests (no external calls)."""

from __future__ import annotations

from app.ai.base import LLMProvider
from app.ai.exceptions import ProviderAuthError
from app.ai.types import LLMRequest, LLMResponse, LLMToolCall, LLMUsage, ProviderTestResult


class FakeLLMProvider(LLMProvider):
    name = "fake"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        settings=None,
        responses: list[LLMResponse] | None = None,
        fail: Exception | None = None,
    ) -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url, settings=settings)
        self._responses = list(responses or [])
        self._fail = fail
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if self._fail is not None:
            raise self._fail
        if self._responses:
            return self._responses.pop(0)
        return LLMResponse(
            content="fake analysis",
            usage=LLMUsage(input_tokens=10, output_tokens=5, total_tokens=15),
            provider=self.name,
            model=self._model,
        )

    async def test_connection(self) -> ProviderTestResult:
        if self._fail is not None:
            raise self._fail
        return ProviderTestResult(ok=True, status="CONNECTED", detail=self._model)


def fake_factory(**overrides):
    """Return a create_provider-compatible callable producing FakeLLMProvider."""

    def _create(*, provider, model, api_key, base_url=None, settings=None):
        return FakeLLMProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
            settings=settings,
            **overrides,
        )

    return _create


__all__ = ["FakeLLMProvider", "fake_factory", "ProviderAuthError", "LLMToolCall"]
