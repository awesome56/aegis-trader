"""Broker connection service (Phase 10).

Encrypted credential storage with masked display; raw secrets are never
returned. External provider adapters are not implemented yet, so Test
Connection reports a normalized ERROR for them (fail closed) while the internal
paper provider reports CONNECTED.
"""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.security import CredentialError, get_cipher
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.broker_connection import BrokerConnection
from app.models.enums import BrokerEnvironment, NotificationSeverity, ProviderStatus
from app.repositories.broker_connection import BrokerConnectionRepository
from app.repositories.notification import SystemEventRepository

# Providers Aegis can name. Only "paper" is implemented; others require a future
# adapter and currently fail closed on connection test.
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
        if connection.provider in IMPLEMENTED_PROVIDERS:
            connection.status = ProviderStatus.CONNECTED
            connection.last_tested_at = _dt.datetime.now(_dt.UTC)
            connection.last_error = None
            connection.updated_at = connection.last_tested_at
            await self._session.flush()
            return True, ProviderStatus.CONNECTED.value, "internal paper broker"
        connection.status = ProviderStatus.ERROR
        connection.last_tested_at = _dt.datetime.now(_dt.UTC)
        connection.last_error = "provider adapter not implemented"
        connection.updated_at = connection.last_tested_at
        await self._session.flush()
        return False, ProviderStatus.ERROR.value, "provider adapter not implemented"

    def decrypt_api_key(self, connection: BrokerConnection) -> str | None:
        if not connection.encrypted_api_key:
            return None
        try:
            return get_cipher(self._settings).decrypt(connection.encrypted_api_key)
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
