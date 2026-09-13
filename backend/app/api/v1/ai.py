"""AI provider REST API (Phase 9A).

Tokens are submitted once and never returned; only a masked suffix is exposed.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.ai.factory import SUPPORTED_PROVIDERS, requires_base_url
from app.ai.service import AIProviderService
from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.models.ai import AIProviderConfig
from app.schemas.ai import (
    ProviderCatalogItem,
    ProviderCatalogSchema,
    ProviderCreateRequest,
    ProviderSchema,
    ProviderTestResponse,
    ProviderUpdateRequest,
)

router = APIRouter(prefix="/ai", tags=["ai"], dependencies=[Depends(get_current_user)])


def _schema(service: AIProviderService, config: AIProviderConfig) -> ProviderSchema:
    return ProviderSchema(
        id=config.id,
        provider=config.provider,
        model=config.model,
        base_url=config.base_url,
        configured=bool(config.encrypted_api_key) or bool(config.api_key_last_four),
        api_key_masked=service.api_key_masked(config),
        enabled=config.enabled,
        is_default=config.is_default,
        status=config.status,
        last_tested_at=config.last_tested_at,
        last_error=config.last_error,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get("/providers", response_model=list[ProviderSchema], summary="List AI providers")
async def list_providers(session: DbSession, user: CurrentUser) -> list[ProviderSchema]:
    service = AIProviderService(session)
    return [_schema(service, config) for config in await service.list(user.id)]


@router.get(
    "/providers/supported",
    response_model=ProviderCatalogSchema,
    summary="Supported providers",
)
async def supported() -> ProviderCatalogSchema:
    items = []
    for key, (_, default_base) in sorted(SUPPORTED_PROVIDERS.items()):
        items.append(
            ProviderCatalogItem(
                key=key,
                requires_base_url=requires_base_url(key),
                default_base_url=default_base,
            )
        )
    return ProviderCatalogSchema(items=items)


@router.post(
    "/providers",
    response_model=ProviderSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create an AI provider config",
)
async def create_provider(
    payload: ProviderCreateRequest, session: DbSession, user: CurrentUser
) -> ProviderSchema:
    service = AIProviderService(session)
    config = await service.create(
        user_id=user.id,
        provider=payload.provider,
        model=payload.model,
        api_key=payload.api_key,
        base_url=payload.base_url,
        enabled=payload.enabled,
        make_default=payload.make_default,
    )
    return _schema(service, config)


@router.get("/providers/{config_id}", response_model=ProviderSchema, summary="AI provider detail")
async def get_provider(
    config_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> ProviderSchema:
    service = AIProviderService(session)
    return _schema(service, await service.get(user.id, config_id))


@router.put("/providers/{config_id}", response_model=ProviderSchema, summary="Update AI provider")
async def update_provider(
    config_id: uuid.UUID,
    payload: ProviderUpdateRequest,
    session: DbSession,
    user: CurrentUser,
) -> ProviderSchema:
    service = AIProviderService(session)
    config = await service.get(user.id, config_id)
    config = await service.update(
        config,
        model=payload.model,
        api_key=payload.api_key,
        base_url=payload.base_url,
        enabled=payload.enabled,
    )
    return _schema(service, config)


@router.delete(
    "/providers/{config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete AI provider",
)
async def delete_provider(
    config_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> None:
    service = AIProviderService(session)
    config = await service.get(user.id, config_id)
    await service.delete(user.id, config)


@router.post(
    "/providers/{config_id}/test",
    response_model=ProviderTestResponse,
    summary="Test provider connection",
)
async def test_provider(
    config_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> ProviderTestResponse:
    service = AIProviderService(session)
    config = await service.get(user.id, config_id)
    result = await service.test(config)
    return ProviderTestResponse(
        ok=result.ok,
        status=result.status,
        detail=result.detail,
        models=[{"id": model.id, "label": model.label} for model in result.models],
    )


@router.post(
    "/providers/{config_id}/activate", response_model=ProviderSchema, summary="Activate provider"
)
async def activate_provider(
    config_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> ProviderSchema:
    service = AIProviderService(session)
    config = await service.get(user.id, config_id)
    config = await service.activate(user.id, config)
    return _schema(service, config)
