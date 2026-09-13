"""LLM provider abstraction.

Agents depend on this interface — never on a concrete provider class. Providers
normalize their external API differences into :mod:`app.ai.types`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.types import LLMMessage, LLMModel, LLMRequest, LLMResponse, ProviderTestResult
from app.core.config import Settings, get_settings


class LLMProvider(ABC):
    name: str = "base"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        base_url: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._settings = settings or get_settings()

    @property
    def model(self) -> str:
        return self._model

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Produce a normalized completion (optionally with tool calls)."""

    async def list_models(self) -> list[LLMModel]:
        return []

    async def test_connection(self) -> ProviderTestResult:
        """Default: perform a minimal generation. Providers may override."""
        response = await self.generate(
            LLMRequest(messages=[LLMMessage(role="user", content="ping")], max_tokens=1)
        )
        return ProviderTestResult(
            ok=True, status="CONNECTED", detail=f"{response.provider}/{response.model}"
        )
