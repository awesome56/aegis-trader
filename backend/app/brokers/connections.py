"""Broker connection service (Phase 10).

Encrypted credential storage with masked display; raw secrets are never
returned. Test Connection calls the provider when an adapter exists (currently
paper and Alpaca) and otherwise reports a normalized ERROR — it never reports
success for a provider it has not really reached.
"""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.security import CredentialError, get_cipher
from app.core.config import Settings, get_settings
from app.core.exceptions import AegisError, ConflictError, NotFoundError, ValidationError
from app.models.broker_connection import BrokerConnection
from app.models.enums import BrokerEnvironment, NotificationSeverity, ProviderStatus
from app.repositories.broker_connection import BrokerConnectionRepository
from app.repositories.notification import SystemEventRepository

# Providers Aegis can name. "paper" is fully implemented; "alpaca" has a real
# adapter (read-side: account/positions/quotes/clock - order routing is still
# fail-closed). Anything else reports ERROR on connection test rather than
# pretending to be reachable.
PROVIDER_CATALOG: dict[str, set[BrokerEnvironment]] = {
    "paper": {BrokerEnvironment.DEMO},
    "alpaca": {BrokerEnvironment.DEMO, BrokerEnvironment.LIVE},
    "oanda": {BrokerEnvironment.DEMO, BrokerEnvironment.LIVE},
    "kraken": {BrokerEnvironment.DEMO, BrokerEnvironment.LIVE},
    "binance": {BrokerEnvironment.DEMO, BrokerEnvironment.LIVE},
    "coinbase": {BrokerEnvironment.DEMO, BrokerEnvironment.LIVE},
    "interactive_brokers": {BrokerEnvironment.DEMO, BrokerEnvironment.LIVE},
}
IMPLEMENTED_PROVIDERS = {"paper"}


class BrokerConnectionService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._connections = BrokerConnectionRepository(session)

    async def list(self, user_id: uuid.UUID) -> list[BrokerConnection]:
        return await self._connections.list_for_user(user_id)

    async def get(self, user_id: uuid.UUID, connection_id: uuid.UUID) -> BrokerConnection:
        connection = await self._connections.get_for_user(connection_id, user_id)
        if connection is None:
            raise NotFoundError(f"Broker connection {connection_id} not found")
        return connection

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        provider: str,
        environment: BrokerEnvironment,
        account_external_id: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        access_token: str | None = None,
        enabled: bool = True,
        make_default: bool = False,
    ) -> BrokerConnection:
        key = provider.strip().lower()
        if key not in PROVIDER_CATALOG:
            raise ValidationError(f"unsupported broker provider {provider!r}")
        if environment not in PROVIDER_CATALOG[key]:
            raise ValidationError(f"provider {key} does not support {environment.value}")
        if environment is BrokerEnvironment.LIVE and not self._settings.LIVE_TRADING_ALLOWED:
            raise ConflictError(
                "live broker connections require LIVE_TRADING_ALLOWED=true on the server"
            )

        cipher = get_cipher(self._settings)
        is_first = not await self._connections.list_for_user(user_id)
        make_default = make_default or is_first
        if make_default:
            await self._connections.clear_defaults(user_id, environment)

        connection = BrokerConnection(
            user_id=user_id,
            provider=key,
            environment=environment,
            account_external_id=account_external_id,
            encrypted_api_key=cipher.encrypt(api_key) if api_key else None,
            encrypted_api_secret=cipher.encrypt(api_secret) if api_secret else None,
            encrypted_access_token=cipher.encrypt(access_token) if access_token else None,
            api_key_last_four=api_key[-4:] if api_key and len(api_key) >= 4 else None,
            enabled=enabled,
            is_default=make_default,
            status=ProviderStatus.UNTESTED,
        )
        await self._connections.add(connection)
        await self._audit(user_id, "broker.connection_configured", key, connection)
        return connection

    async def update(
        self,
        connection: BrokerConnection,
        *,
        account_external_id: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        access_token: str | None = None,
        enabled: bool | None = None,
    ) -> BrokerConnection:
        cipher = get_cipher(self._settings)
        if account_external_id is not None:
            connection.account_external_id = account_external_id
        if api_key:
            connection.encrypted_api_key = cipher.encrypt(api_key)
            connection.api_key_last_four = api_key[-4:] if len(api_key) >= 4 else None
        if api_secret:
            connection.encrypted_api_secret = cipher.encrypt(api_secret)
        if access_token:
            connection.encrypted_access_token = cipher.encrypt(access_token)
        if enabled is not None:
            connection.enabled = enabled
            connection.status = ProviderStatus.UNTESTED if enabled else ProviderStatus.DISABLED
        connection.status = ProviderStatus.UNTESTED
        connection.updated_at = _dt.datetime.now(_dt.UTC)
        await self._session.flush()
        return connection

    async def delete(self, user_id: uuid.UUID, connection: BrokerConnection) -> None:
        was_default = connection.is_default
        environment = connection.environment
        provider = connection.provider
        await self._connections.delete(connection)
        if was_default:
            remaining = [
                row
                for row in await self._connections.list_for_user(user_id)
                if row.environment is environment
            ]
            if remaining:
                remaining[0].is_default = True
                await self._session.flush()
        await self._audit(user_id, "broker.connection_removed", provider, connection)

    async def activate(self, user_id: uuid.UUID, connection: BrokerConnection) -> BrokerConnection:
        if not connection.enabled:
            raise ConflictError("cannot activate a disabled connection")
        await self._connections.clear_defaults(user_id, connection.environment)
        connection.is_default = True
        connection.updated_at = _dt.datetime.now(_dt.UTC)
        await self._session.flush()
        await self._audit(user_id, "broker.connection_activated", connection.provider, connection)
        return connection

    async def test(self, connection: BrokerConnection) -> tuple[bool, str, str | None]:
        """Return ``(ok, status, detail)``. Fail closed for unimplemented providers."""
        if connection.provider == "alpaca":
            return await self._test_alpaca(connection)
        if connection.provider in IMPLEMENTED_PROVIDERS:
            return await self._record_test(
                connection, ok=True, detail="internal paper broker"
            )
        return await self._record_test(
            connection, ok=False, detail="provider adapter not implemented"
        )

    async def _record_test(
        self,
        connection: BrokerConnection,
        *,
        ok: bool,
        detail: str,
        error: str | None = None,
    ) -> tuple[bool, str, str | None]:
        now = _dt.datetime.now(_dt.UTC)
        connection.status = ProviderStatus.CONNECTED if ok else ProviderStatus.ERROR
        connection.last_tested_at = now
        connection.last_error = None if ok else (error or detail)
        connection.updated_at = now
        await self._session.flush()
        return ok, connection.status.value, detail

    async def _test_alpaca(self, connection: BrokerConnection) -> tuple[bool, str, str | None]:
        """Reach the real Alpaca endpoint with the stored credentials."""
        from app.brokers.alpaca.client import AlpacaClient

        api_key = self.decrypt_api_key(connection)
        api_secret = self.decrypt_api_secret(connection)
        if not api_key or not api_secret:
            return await self._record_test(
                connection,
                ok=False,
                detail="missing Alpaca API key/secret",
                error="missing Alpaca API key/secret",
            )
        client = AlpacaClient(
            api_key=api_key, api_secret=api_secret, environment=connection.environment
        )
        try:
            account = await client.get_account()
        except AegisError as exc:
            return await self._record_test(
                connection, ok=False, detail=exc.message, error=exc.message
            )
        finally:
            await client.aclose()
        external = account.get("account_number") if isinstance(account, dict) else None
        if external:
            connection.account_external_id = str(external)
        return await self._record_test(
            connection, ok=True, detail=f"Alpaca account {external or 'verified'}"
        )

    def decrypt_api_key(self, connection: BrokerConnection) -> str | None:
        return self._decrypt(connection.encrypted_api_key)

    def decrypt_api_secret(self, connection: BrokerConnection) -> str | None:
        return self._decrypt(connection.encrypted_api_secret)

    def decrypt_access_token(self, connection: BrokerConnection) -> str | None:
        return self._decrypt(connection.encrypted_access_token)

    def _decrypt(self, encrypted: str | None) -> str | None:
        if not encrypted:
            return None
        try:
            return get_cipher(self._settings).decrypt(encrypted)
        except CredentialError:
            return None

    def masked(self, connection: BrokerConnection) -> str | None:
        return f"••••••{connection.api_key_last_four}" if connection.api_key_last_four else None

    async def _audit(
        self,
        user_id: uuid.UUID,
        event_type: str,
        provider: str,
        connection: BrokerConnection,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> None:
        await SystemEventRepository(self._session).record(
            event_type=event_type,
            source="broker",
            message=f"Broker connection {provider} ({connection.environment.value})",
            severity=severity,
            actor=str(user_id),
            payload={
                "provider": provider,
                "environment": connection.environment.value,
                "connection_id": str(connection.id),
            },
        )
