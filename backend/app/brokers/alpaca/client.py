"""Async Alpaca REST client.

Transport only: no trading logic, no persistence, no credential storage. Every
provider failure is normalised into an :mod:`app.brokers.exceptions` error so
nothing above the broker layer knows Alpaca's wire format.

Environment wiring: Alpaca's *paper* endpoint
(``https://paper-api.alpaca.markets``) backs :attr:`BrokerEnvironment.DEMO`; the
live endpoint (``https://api.alpaca.markets``) backs
:attr:`BrokerEnvironment.LIVE` and is only constructed when the caller has
already passed the live-trading interlock.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.brokers.exceptions import (
    BrokerAuthenticationError,
    BrokerConfigurationError,
    BrokerRejectedOrderError,
    BrokerUnavailableError,
    InsufficientFundsError,
    InsufficientPositionError,
)
from app.core.logging import get_logger
from app.models.enums import BrokerEnvironment

logger = get_logger(__name__)

ALPACA_TRADING_BASE_URLS: dict[BrokerEnvironment, str] = {
    BrokerEnvironment.DEMO: "https://paper-api.alpaca.markets",
    BrokerEnvironment.LIVE: "https://api.alpaca.markets",
}
ALPACA_DATA_BASE_URL = "https://data.alpaca.markets"

DEFAULT_TIMEOUT_SECONDS = 10.0


class AlpacaClient:
    """Thin async wrapper over the Alpaca trading and market-data REST APIs."""

    def __init__(
        self,
        *,
        api_key: str | None,
        api_secret: str | None,
        environment: BrokerEnvironment,
        trading_base_url: str | None = None,
        data_base_url: str = ALPACA_DATA_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key or not api_secret:
            raise BrokerConfigurationError(
                "Alpaca requires an API key and secret",
                details={"provider": "alpaca"},
            )
        self._environment = environment
        self._trading_base_url = (
            trading_base_url or ALPACA_TRADING_BASE_URLS[environment]
        ).rstrip("/")
        self._data_base_url = data_base_url.rstrip("/")
        self._headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
            "Accept": "application/json",
        }
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=timeout, transport=transport, headers=self._headers
        )

    # --- lifecycle ----------------------------------------------------------
    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AlpacaClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    @property
    def environment(self) -> BrokerEnvironment:
        return self._environment

    @property
    def trading_base_url(self) -> str:
        return self._trading_base_url

    # --- transport ----------------------------------------------------------
    async def _request(
        self,
        method: str,
        path: str,
        *,
        base: str = "trading",
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        allow_not_found: bool = False,
    ) -> Any:
        root = self._data_base_url if base == "data" else self._trading_base_url
        url = f"{root}{path}"
        try:
            response = await self._client.request(
                method, url, params=params, json=json, headers=self._headers
            )
        except httpx.HTTPError as exc:
            raise BrokerUnavailableError(
                f"Alpaca request failed: {exc}",
                details={"provider": "alpaca", "path": path},
            ) from exc

        if response.status_code == 404 and allow_not_found:
            return None
        if response.status_code >= 400:
            raise self._normalize_error(response, path=path)
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise BrokerUnavailableError(
                "Alpaca returned a malformed response", details={"provider": "alpaca"}
            ) from exc

    @staticmethod
    def _error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or f"HTTP {response.status_code}"
        if isinstance(payload, dict):
            message = payload.get("message")
            if isinstance(message, str) and message:
                return message
        return f"HTTP {response.status_code}"

    def _normalize_error(self, response: httpx.Response, *, path: str) -> Exception:
        status = response.status_code
        message = self._error_message(response)
        details = {"provider": "alpaca", "path": path, "status": status}
        if status in (401, 403):
            return BrokerAuthenticationError(
                f"Alpaca authentication failed: {message}", details=details
            )
        if status == 404:
            return BrokerRejectedOrderError(
                f"Alpaca resource not found: {message}", details=details
            )
        if status == 429:
            return BrokerUnavailableError(f"Alpaca rate limited: {message}", details=details)
        if status == 422:
            lowered = message.lower()
            if "insufficient" in lowered:
                if "position" in lowered or "shares" in lowered:
                    return InsufficientPositionError(message, details=details)
                return InsufficientFundsError(message, details=details)
            return BrokerRejectedOrderError(message, details=details)
        if status >= 500:
            return BrokerUnavailableError(f"Alpaca unavailable: {message}", details=details)
        return BrokerRejectedOrderError(message, details=details)

    # --- account / positions ------------------------------------------------
    async def get_account(self) -> dict[str, Any]:
        return await self._request("GET", "/v2/account")

    async def get_positions(self) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/v2/positions")
        return list(payload or [])

    async def get_position(self, symbol: str) -> dict[str, Any] | None:
        return await self._request(
            "GET", f"/v2/positions/{symbol}", allow_not_found=True
        )

    # --- orders -------------------------------------------------------------
    async def get_clock(self) -> dict[str, Any]:
        return await self._request("GET", "/v2/clock")

    async def list_orders(
        self, *, status: str | None = None, limit: int = 50, direction: str = "desc"
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"direction": direction, "limit": limit}
        if status:
            params["status"] = status
        payload = await self._request("GET", "/v2/orders", params=params)
        return list(payload or [])

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        return await self._request(
            "GET", f"/v2/orders/{order_id}", allow_not_found=True
        )

    async def submit_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/v2/orders", json=payload)

    async def cancel_order(self, order_id: str) -> None:
        await self._request("DELETE", f"/v2/orders/{order_id}")

    # --- market data --------------------------------------------------------
    async def get_snapshot(self, symbol: str) -> dict[str, Any] | None:
        """Latest trade/quote snapshot for a US equity symbol."""
        return await self._request(
            "GET", f"/v2/stocks/{symbol.upper()}/snapshot", base="data", allow_not_found=True
        )
