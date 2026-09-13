"""Google Gemini generateContent provider."""

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

DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"


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


class GeminiProvider(LLMProvider):
    name = "gemini"

    def _url(self) -> str:
        base = (self._base_url or DEFAULT_BASE_URL).rstrip("/")
        return f"{base}/v1beta/models/{self._model}:generateContent"

    def _payload(self, request: LLMRequest) -> dict:
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in request.messages
            if m.role in ("user", "assistant")
        ]
        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens or 1024,
            },
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
        if request.tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.parameters,
                        }
                        for tool in request.tools
                    ]
                }
            ]
        return payload

    async def generate(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._settings.AI_HTTP_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    self._url(), params={"key": self._api_key}, json=self._payload(request)
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("provider request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError("provider is unreachable") from exc
        if response.status_code >= 400:
            raise _classify(response.status_code, response.text)

        try:
            body = response.json()
            candidate = body["candidates"][0]
            parts = candidate.get("content", {}).get("parts", [])
        except (KeyError, IndexError, ValueError) as exc:
            raise ProviderResponseError("provider returned an unexpected payload") from exc

        text_parts: list[str] = []
        tool_calls: list[LLMToolCall] = []
        for index, part in enumerate(parts):
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                call = part["functionCall"]
                tool_calls.append(
                    LLMToolCall(
                        id=f"gemini-{index}",
                        name=call.get("name", ""),
                        arguments=call.get("args") or {},
                    )
                )
        usage_raw = body.get("usageMetadata") or {}
        prompt_tokens = int(usage_raw.get("promptTokenCount", 0) or 0)
        completion_tokens = int(usage_raw.get("candidatesTokenCount", 0) or 0)
        return LLMResponse(
            content="\n".join(text_parts),
            tool_calls=tool_calls,
            usage=LLMUsage(
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                total_tokens=int(
                    usage_raw.get("totalTokenCount", prompt_tokens + completion_tokens) or 0
                ),
            ),
            provider=self.name,
            model=self._model,
            finish_reason=candidate.get("finishReason"),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def test_connection(self) -> ProviderTestResult:
        response = await self.generate(
            LLMRequest(messages=[LLMMessage(role="user", content="ping")], max_tokens=1)
        )
        return ProviderTestResult(ok=True, status="CONNECTED", detail=response.model)
