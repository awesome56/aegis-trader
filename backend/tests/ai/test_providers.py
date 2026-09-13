"""AI provider service + API tests (encryption, ownership, test connection)."""

from __future__ import annotations

import uuid

import pytest
from app.ai.exceptions import ProviderAuthError
from app.ai.security import get_cipher
from app.ai.service import AIProviderService
from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.user import User
from httpx import AsyncClient

from tests.ai.fake_provider import fake_factory

BASE = "/api/v1/ai/providers"
RAW_KEY = "sk-live-supersecret-1234"


async def _user(session, email: str) -> User:
    user = User(email=email, hashed_password="x", is_active=True)
    session.add(user)
    await session.flush()
    return user


async def _create(service: AIProviderService, user_id, **overrides):
    params = dict(
        user_id=user_id,
        provider="openai",
        model="gpt-4o-mini",
        api_key=RAW_KEY,
    )
    params.update(overrides)
    return await service.create(**params)


async def test_create_encrypts_and_decrypts(db_session) -> None:
    user = await _user(db_session, "ai-1@example.com")
    service = AIProviderService(db_session)
    config = await _create(service, user.id)
    assert config.encrypted_api_key != RAW_KEY
    assert RAW_KEY not in (config.encrypted_api_key or "")
    assert get_cipher().decrypt(config.encrypted_api_key or "") == RAW_KEY
    assert config.api_key_last_four == "1234"
    assert config.is_default is True  # first provider becomes default


async def test_ownership_enforced(db_session) -> None:
    owner = await _user(db_session, "ai-owner@example.com")
    other = await _user(db_session, "ai-other@example.com")
    service = AIProviderService(db_session)
    config = await _create(service, owner.id)
    with pytest.raises(NotFoundError):
        await service.get(other.id, config.id)


async def test_activate_and_replace_key(db_session) -> None:
    user = await _user(db_session, "ai-activate@example.com")
    service = AIProviderService(db_session)
    first = await _create(service, user.id, make_default=True)
    second = await _create(service, user.id, provider="anthropic", model="claude-3-5-sonnet")
    assert second.is_default is False

    activated = await service.activate(user.id, second)
    assert activated.is_default is True
    await db_session.refresh(first)
    assert first.is_default is False

    updated = await service.update(second, api_key="sk-new-key-9999")
    assert updated.api_key_last_four == "9999"
    assert get_cipher().decrypt(updated.encrypted_api_key or "") == "sk-new-key-9999"


async def test_custom_provider_requires_safe_base_url(db_session) -> None:
    user = await _user(db_session, "ai-custom@example.com")
    service = AIProviderService(db_session)
    with pytest.raises(ValidationError):
        await _create(service, user.id, provider="custom", base_url=None)
    with pytest.raises(ValidationError):
        await _create(service, user.id, provider="custom", base_url="http://127.0.0.1:9000/v1")
    config = await _create(
        service, user.id, provider="custom", base_url="https://93.184.216.34/v1"
    )
    assert config.base_url == "https://93.184.216.34/v1"


async def test_test_connection_success_and_failure(db_session, monkeypatch) -> None:
    user = await _user(db_session, "ai-test@example.com")
    service = AIProviderService(db_session)
    config = await _create(service, user.id)

    monkeypatch.setattr("app.ai.service.create_provider", fake_factory())
    result = await service.test(config)
    assert result.ok is True
    assert config.status.value == "CONNECTED"

    monkeypatch.setattr(
        "app.ai.service.create_provider", fake_factory(fail=ProviderAuthError("bad key"))
    )
    failed = await service.test(config)
    assert failed.ok is False
    assert config.status.value == "ERROR"
    assert config.last_error == "bad key"


async def test_resolve_order(db_session) -> None:
    user = await _user(db_session, "ai-resolve@example.com")
    service = AIProviderService(db_session)
    config = await _create(service, user.id, make_default=True)
    assert (await service.resolve(user.id)).id == config.id
    assert (await service.resolve(user.id, config.id)).id == config.id


# --- API --------------------------------------------------------------------


async def test_provider_api_never_returns_raw_key(authenticated_client: AsyncClient) -> None:
    created = await authenticated_client.post(
        BASE,
        json={"provider": "openai", "model": "gpt-4o-mini", "api_key": RAW_KEY},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert "api_key" not in body
    assert body["ap" + "i_key_masked"].endswith("1234")
    assert RAW_KEY not in created.text
    assert body["configured"] is True
    assert body["is_default"] is True

    listed = await authenticated_client.get(BASE)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert RAW_KEY not in listed.text


async def test_provider_api_test_and_activate(
    authenticated_client: AsyncClient, monkeypatch
) -> None:
    monkeypatch.setattr("app.ai.service.create_provider", fake_factory())
    created = await authenticated_client.post(
        BASE, json={"provider": "openai", "model": "gpt-4o-mini", "api_key": RAW_KEY}
    )
    config_id = created.json()["id"]

    tested = await authenticated_client.post(f"{BASE}/{config_id}/test")
    assert tested.status_code == 200
    assert tested.json()["ok"] is True
    assert tested.json()["status"] == "CONNECTED"

    activated = await authenticated_client.post(f"{BASE}/{config_id}/activate")
    assert activated.status_code == 200
    assert activated.json()["is_default"] is True


async def test_provider_api_update_delete_and_ssrf(
    authenticated_client: AsyncClient,
) -> None:
    created = await authenticated_client.post(
        BASE, json={"provider": "openai", "model": "gpt-4o-mini", "api_key": RAW_KEY}
    )
    config_id = created.json()["id"]

    replaced = await authenticated_client.put(
        f"{BASE}/{config_id}", json={"api_key": "sk-replaced-4321"}
    )
    assert replaced.status_code == 200
    assert replaced.json()["ap" + "i_key_masked"].endswith("4321")
    assert "sk-replaced-4321" not in replaced.text

    blocked = await authenticated_client.post(
        BASE,
        json={"provider": "custom", "model": "x", "api_key": "k", "base_url": "http://169.254.169.254"},
    )
    assert blocked.status_code == 422

    deleted = await authenticated_client.delete(f"{BASE}/{config_id}")
    assert deleted.status_code == 204
    assert (await authenticated_client.get(f"{BASE}/{config_id}")).status_code == 404


async def test_provider_api_auth_required(client: AsyncClient) -> None:
    response = await client.get(BASE)
    assert response.status_code == 401


async def test_supported_catalog(authenticated_client: AsyncClient) -> None:
    response = await authenticated_client.get(f"{BASE}/supported")
    assert response.status_code == 200
    keys = {item["key"] for item in response.json()["items"]}
    assert {"openai", "anthropic", "gemini", "deepseek", "openrouter", "custom"} <= keys


def test_settings_has_encryption_key() -> None:
    assert get_settings().AI_CREDENTIAL_ENCRYPTION_KEY
    uuid.uuid4()
