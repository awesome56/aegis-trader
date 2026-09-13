"""AI provider configuration service (Phase 9A).

Handles encrypted credential storage, activation, connection testing and
provider resolution. Raw API tokens never leave this layer in plaintext.
"""

from __future__ import annotations

import datetime as _dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.exceptions import LLMProviderError
from app.ai.factory import (
    create_provider,
    normalise_provider,
    requires_base_url,
    supported_providers,
)
from app.ai.security import CredentialError, get_cipher
from app.ai.types import ProviderTestResult
from app.ai.urlsafety import UnsafeBaseUrlError, validate_base_url
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.ai import AIProviderConfig
from app.models.enums import NotificationSeverity, ProviderStatus
from app.repositories.ai import AIProviderConfigRepository
from app.repositories.notification import SystemEventRepository


class AIProviderService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._configs = AIProviderConfigRepository(session)

    # --- CRUD ---------------------------------------------------------------
    async def list(self, user_id: uuid.UUID) -> list[AIProviderConfig]:
        return await self._configs.list_for_user(user_id)

    async def get(self, user_id: uuid.UUID, config_id: uuid.UUID) -> AIProviderConfig:
        config = await self._configs.get_for_user(config_id, user_id)
        if config is None:
            raise NotFoundError(f"Provider config {config_id} not found")
        return config

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        provider: str,
        model: str,
        api_key: str,
        base_url: str | None = None,
        enabled: bool = True,
        make_default: bool = False,
    ) -> AIProviderConfig:
        if not self._settings.AI_ENABLED:
            raise ConflictError("AI features are disabled")
        key = normalise_provider(provider)
        if key not in supported_providers():
            raise ValidationError(f"unsupported provider {provider!r}")
        if not model.strip():
            raise ValidationError("model is required")
        if not api_key.strip():
            raise ValidationError("api_key is required")
        cleaned_url = self._validate_base_url(key, base_url)

        cipher = self._cipher()
        is_first = await self._configs.count_for_user(user_id) == 0
        make_default = make_default or is_first
        if make_default:
            await self._configs.clear_defaults(user_id)

        config = AIProviderConfig(
            user_id=user_id,
            provider=key,
            model=model.strip(),
            base_url=cleaned_url,
            encrypted_api_key=cipher.encrypt(api_key.strip()),
            api_key_last_four=api_key.strip()[-4:],
            enabled=enabled,
            is_default=make_default,
            status=ProviderStatus.UNTESTED,
        )
        await self._configs.add(config)
        await self._audit(user_id, "ai.provider_configured", f"Provider {key} configured", config)
        return config

    async def update(
        self,
        config: AIProviderConfig,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        enabled: bool | None = None,
    ) -> AIProviderConfig:
        if model is not None:
            if not model.strip():
                raise ValidationError("model cannot be empty")
            config.model = model.strip()
        if api_key is not None:
            if not api_key.strip():
                raise ValidationError("api_key cannot be empty")
            config.encrypted_api_key = self._cipher().encrypt(api_key.strip())
            config.api_key_last_four = api_key.strip()[-4:]
        if base_url is not None:
            config.base_url = self._validate_base_url(config.provider, base_url or None)
        if enabled is not None:
            config.enabled = enabled
            config.status = ProviderStatus.UNTESTED if enabled else ProviderStatus.DISABLED
        config.status = ProviderStatus.UNTESTED
        config.updated_at = _dt.datetime.now(_dt.UTC)
        await self._session.flush()
        return config

    async def delete(self, user_id: uuid.UUID, config: AIProviderConfig) -> None:
        was_default = config.is_default
        provider = config.provider
        await self._configs.delete(config)
        if was_default:
            remaining = await self._configs.list_for_user(user_id)
            if remaining:
                remaining[0].is_default = True
                await self._session.flush()
        await self._session.flush()
        await self._audit(user_id, "ai.provider_removed", f"Provider {provider} removed", config)

    async def activate(self, user_id: uuid.UUID, config: AIProviderConfig) -> AIProviderConfig:
        if not config.enabled:
            raise ConflictError("cannot activate a disabled provider")
        await self._configs.clear_defaults(user_id)
        config.is_default = True
        config.updated_at = _dt.datetime.now(_dt.UTC)
        await self._session.flush()
        await self._audit(
            user_id, "ai.provider_activated", f"Provider {config.provider} activated", config
        )
        return config

    # --- connection test ----------------------------------------------------
    async def test(self, config: AIProviderConfig) -> ProviderTestResult:
        try:
            api_key = self.decrypt_key(config)
        except CredentialError as exc:
            return await self._record_test(config, False, ProviderStatus.ERROR, str(exc))
        try:
            provider = create_provider(
                provider=config.provider,
                model=config.model,
                api_key=api_key,
                base_url=config.base_url,
                settings=self._settings,
            )
            result = await provider.test_connection()
        except LLMProviderError as exc:
            return await self._record_test(config, False, ProviderStatus.ERROR, exc.message)
        except Exception:  # noqa: BLE001 - never leak provider internals
            return await self._record_test(
                config, False, ProviderStatus.ERROR, "provider connection failed"
            )
        return await self._record_test(
            config, True, ProviderStatus.CONNECTED, result.detail, result
        )

    async def _record_test(
        self,
        config: AIProviderConfig,
        ok: bool,
        status: ProviderStatus,
        detail: str | None,
        result: ProviderTestResult | None = None,
    ) -> ProviderTestResult:
        config.status = status
        config.last_tested_at = _dt.datetime.now(_dt.UTC)
        config.last_error = None if ok else (detail or "connection failed")
        config.updated_at = _dt.datetime.now(_dt.UTC)
        await self._session.flush()
        if not ok:
            await self._audit(
                config.user_id,
                "ai.provider_connection_failed",
                f"Provider {config.provider} connection failed",
                config,
                severity=NotificationSeverity.WARNING,
            )
        return result or ProviderTestResult(ok=ok, status=status.value, detail=detail)

    # --- resolution ---------------------------------------------------------
    async def resolve(
        self, user_id: uuid.UUID, provider_config_id: uuid.UUID | None = None
    ) -> AIProviderConfig | None:
        """Selection order: explicit id → user default → server-level env fallback."""
        if provider_config_id is not None:
            config = await self._configs.get_for_user(provider_config_id, user_id)
            if config is None:
                raise NotFoundError(f"Provider config {provider_config_id} not found")
            return config if config.enabled else None
        default = await self._configs.get_default_for_user(user_id)
        if default is not None and default.enabled:
            return default
        if self._settings.LLM_API_KEY and self._settings.LLM_MODEL:
            return AIProviderConfig(
                id=uuid.uuid4(),
                user_id=user_id,
                provider=normalise_provider(self._settings.LLM_PROVIDER),
                model=self._settings.LLM_MODEL,
                encrypted_api_key=None,
                enabled=True,
                is_default=True,
                status=ProviderStatus.CONNECTED,
            )
        return None

    def decrypt_key(self, config: AIProviderConfig) -> str:
        if not config.encrypted_api_key:
            if config.provider and self._settings.LLM_API_KEY:
                return self._settings.LLM_API_KEY
            raise CredentialError("provider has no stored credential")
        return self._cipher().decrypt(config.encrypted_api_key)

    def api_key_masked(self, config: AIProviderConfig) -> str | None:
        if config.api_key_last_four:
            return f"••••••{config.api_key_last_four}"
        return None

    # --- helpers ------------------------------------------------------------
    def _cipher(self):  # noqa: ANN202
        return get_cipher(self._settings)

    def _validate_base_url(self, provider: str, base_url: str | None) -> str | None:
        if not base_url:
            if requires_base_url(provider):
                raise ValidationError("base_url is required for a custom provider")
            return None
        if not self._settings.AI_ALLOW_CUSTOM_BASE_URL and normalise_provider(provider) == "custom":
            raise ValidationError("custom base URLs are disabled")
        try:
            return validate_base_url(base_url, self._settings)
        except UnsafeBaseUrlError as exc:
            raise ValidationError(str(exc)) from exc

    async def _audit(
        self,
        user_id: uuid.UUID,
        event_type: str,
        message: str,
        config: AIProviderConfig,
        *,
        severity: NotificationSeverity = NotificationSeverity.INFO,
    ) -> None:
        await SystemEventRepository(self._session).record(
            event_type=event_type,
            source="ai",
            message=message,
            severity=severity,
            actor=str(user_id),
            payload={"provider": config.provider, "config_id": str(config.id)},
        )
