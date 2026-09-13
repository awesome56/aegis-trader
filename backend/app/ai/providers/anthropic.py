"""Anthropic Messages API provider."""

from __future__ import annotations

import time

import httpx

from app.ai.base import LLMProvider
from app.ai.exceptions import (
    ProviderAuthError,
    ProviderModelError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.ai.types import (
    LLMMessage,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
    ProviderTestResult,
)

DEFAULT_BASE_URL = "https://api.anthropic.com"
API_VERSION = "2023-06-01"


def _classify(status_code: int, detail: str) -> Exception:
    if status_code in (401, 403):
        return ProviderAuthError("provider rejected the credential")
    if status_code == 404:
        return ProviderModelError("unknown model or endpoint")
    if status_code == 429:
        return ProviderRateLimitError("provider rate limit reached")
    if status_code >= 500:
        return ProviderUnavailableError(f"provider error ({status_code})")
    return ProviderResponseError(detail[:200] or f"provider returned {status_code}")


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def _url(self, path: str) -> str:
        return f"{(self._base_url or DEFAULT_BASE_URL).rstrip('/')}{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self._api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }

    def _payload(self, request: LLMRequest) -> dict:
        messages = [
            {"role": m.role, "content": m.content}
            for m in request.messages
            if m.role in ("user", "assistant")
        ]
        payload: dict = {
            "model": self._model,
            "max_tokens": request.max_tokens or 1024,
            "temperature": request.temperature,
            "messages": messages,
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        if request.tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in request.tools
            ]
        return payload

    async def generate(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._settings.AI_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    self._url("/v1/messages"), headers=self._headers(), json=self._payload(request)
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("provider request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("provider is unreachable") from exc
        if response.status_code >= 400:
            raise _classify(response.status_code, response.text)

        try:
            body = response.json()
            blocks = body.get("content", [])
        except ValueError as exc:
            raise ProviderResponseError("provider returned an unexpected payload") from exc

        text_parts: list[str] = []
        tool_calls: list[LLMToolCall] = []
        for block in blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    LLMToolCall(
                        id=block.get("id", ""),
                        name=block.get("name", ""),
                        arguments=block.get("input") or {},
                    )
                )
        usage_raw = body.get("usage") or {}
        prompt_tokens = int(usage_raw.get("input_tokens", 0) or 0)
        completion_tokens = int(usage_raw.get("output_tokens", 0) or 0)
        return LLMResponse(
            content="\n".join(part for part in text_parts if part),
            tool_calls=tool_calls,
            usage=LLMUsage(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            provider=self.name,
            model=self._model,
            request_id=body.get("id"),
            finish_reason=body.get("stop_reason"),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def test_connection(self) -> ProviderTestResult:
        response = await self.generate(
            LLMRequest(messages=[LLMMessage(role="user", content="ping")], max_tokens=1)
        )
        return ProviderTestResult(ok=True, status="CONNECTED", detail=response.model)
