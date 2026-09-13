"""OpenAI-compatible chat provider.

Covers OpenAI, DeepSeek, OpenRouter and custom OpenAI-compatible endpoints.
"""

from __future__ import annotations

import json
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
    LLMModel,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
    LLMUsage,
    ProviderTestResult,
)

DEFAULT_BASE_URL = "https://api.openai.com/v1"


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


class OpenAICompatibleProvider(LLMProvider):
    name = "openai"

    def _url(self, path: str) -> str:
        base = (self._base_url or DEFAULT_BASE_URL).rstrip("/")
        return f"{base}{path}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _payload(self, request: LLMRequest) -> dict:
        messages: list[dict] = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        for message in request.messages:
            entry: dict = {"role": message.role, "content": message.content}
            if message.tool_call_id:
                entry["tool_call_id"] = message.tool_call_id
            if message.name:
                entry["name"] = message.name
            messages.append(entry)
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            payload["max_tokens"] = request.max_tokens
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in request.tools
            ]
        return payload

    async def generate(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._settings.AI_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    self._url("/chat/completions"),
                    headers=self._headers(),
                    json=self._payload(request),
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("provider request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("provider is unreachable") from exc

        if response.status_code >= 400:
            raise _classify(response.status_code, response.text)

        try:
            body = response.json()
            choice = body["choices"][0]
            message = choice.get("message", {})
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderResponseError("provider returned an unexpected payload") from exc

        tool_calls: list[LLMToolCall] = []
        for call in message.get("tool_calls") or []:
            function = call.get("function", {})
            raw_args = function.get("arguments") or "{}"
            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append(
                LLMToolCall(
                    id=call.get("id", ""), name=function.get("name", ""), arguments=arguments
                )
            )

        usage_raw = body.get("usage") or {}
        usage = LLMUsage(
            input_tokens=int(usage_raw.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage_raw.get("completion_tokens", 0) or 0),
            total_tokens=int(usage_raw.get("total_tokens", 0) or 0),
        )
        return LLMResponse(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            usage=usage,
            provider=self.name,
            model=self._model,
            request_id=body.get("id"),
            finish_reason=choice.get("finish_reason"),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def list_models(self) -> list[LLMModel]:
        try:
            async with httpx.AsyncClient(timeout=self._settings.AI_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.get(self._url("/models"), headers=self._headers())
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("provider is unreachable") from exc
        if response.status_code >= 400:
            raise _classify(response.status_code, response.text)
        data = response.json().get("data", [])
        return [
            LLMModel(id=row.get("id", ""), label=row.get("id"))
            for row in data
            if row.get("id")
        ]

    async def test_connection(self) -> ProviderTestResult:
        try:
            models = await self.list_models()
            return ProviderTestResult(ok=True, status="CONNECTED", models=models[:50])
        except ProviderModelError:
            # Endpoint may not expose /models; fall back to a minimal generation.
            response = await self.generate(
                LLMRequest(messages=[LLMMessage(role="user", content="ping")], max_tokens=1)
            )
            return ProviderTestResult(ok=True, status="CONNECTED", detail=response.model)
