"""Provider registry + factory. Agents depend on the abstraction only."""

from __future__ import annotations

from app.ai.base import LLMProvider
from app.ai.exceptions import ProviderModelError
from app.ai.providers.anthropic import DEFAULT_BASE_URL as ANTHROPIC_BASE
from app.ai.providers.anthropic import AnthropicProvider
from app.ai.providers.gemini import DEFAULT_BASE_URL as GEMINI_BASE
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.openai_compatible import DEFAULT_BASE_URL as OPENAI_BASE
from app.ai.providers.openai_compatible import OpenAICompatibleProvider
from app.core.config import Settings, get_settings

DEEPSEEK_BASE = "https://api.deepseek.com/v1"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"

# provider key -> (implementation, default base url or None)
SUPPORTED_PROVIDERS: dict[str, tuple[type[LLMProvider], str | None]] = {
    "openai": (OpenAICompatibleProvider, OPENAI_BASE),
    "deepseek": (OpenAICompatibleProvider, DEEPSEEK_BASE),
    "openrouter": (OpenAICompatibleProvider, OPENROUTER_BASE),
    "custom": (OpenAICompatibleProvider, None),
    "anthropic": (AnthropicProvider, ANTHROPIC_BASE),
    "gemini": (GeminiProvider, GEMINI_BASE),
}


def normalise_provider(name: str) -> str:
    return name.strip().lower()


def requires_base_url(provider: str) -> bool:
    return normalise_provider(provider) == "custom"


def supported_providers() -> list[str]:
    return sorted(SUPPORTED_PROVIDERS)


def create_provider(
    *,
    provider: str,
    model: str,
    api_key: str,
    base_url: str | None = None,
    settings: Settings | None = None,
) -> LLMProvider:
    key = normalise_provider(provider)
    entry = SUPPORTED_PROVIDERS.get(key)
    if entry is None:
        raise ProviderModelError(f"unsupported provider {provider!r}")
    implementation, default_base = entry
    if requires_base_url(key) and not base_url:
        raise ProviderModelError("custom provider requires a base_url")
    return implementation(
        api_key=api_key,
        model=model,
        base_url=base_url or default_base,
        settings=settings or get_settings(),
    )
