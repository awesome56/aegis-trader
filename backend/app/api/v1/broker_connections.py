"""Broker connections API (Phase 10). Raw credentials are never returned."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import CurrentUser, DbSession, get_current_user
from app.brokers.connections import BrokerConnectionService
from app.models.broker_connection import BrokerConnection
from app.schemas.trading_control import (
    BrokerConnectionCreateRequest,
    BrokerConnectionSchema,
    BrokerConnectionTestResponse,
    BrokerConnectionUpdateRequest,
)

router = APIRouter(
    prefix="/brokers", tags=["brokers"], dependencies=[Depends(get_current_user)]
)


def _schema(service: BrokerConnectionService, row: BrokerConnection) -> BrokerConnectionSchema:
    return BrokerConnectionSchema(
        id=row.id,
        provider=row.provider,
        environment=row.environment,
        account_external_id=row.account_external_id,
        configured=bool(row.encrypted_api_key or row.encrypted_access_token),
        api_key_masked=service.masked(row),
        enabled=row.enabled,
        is_default=row.is_default,
        status=row.status,
        last_tested_at=row.last_tested_at,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/connections", response_model=list[BrokerConnectionSchema])
async def list_connections(session: DbSession, user: CurrentUser) -> list[BrokerConnectionSchema]:
    service = BrokerConnectionService(session)
    return [_schema(service, row) for row in await service.list(user.id)]


@router.post(
    "/connections", response_model=BrokerConnectionSchema, status_code=status.HTTP_201_CREATED
)
async def create_connection(
    payload: BrokerConnectionCreateRequest, session: DbSession, user: CurrentUser
) -> BrokerConnectionSchema:
    service = BrokerConnectionService(session)
    row = await service.create(
        user_id=user.id,
        provider=payload.provider,
        environment=payload.environment,
        account_external_id=payload.account_external_id,
        api_key=payload.api_key,
        api_secret=payload.api_secret,
        access_token=payload.access_token,
        enabled=payload.enabled,
        make_default=payload.make_default,
    )
    return _schema(service, row)


@router.get("/connections/{connection_id}", response_model=BrokerConnectionSchema)
async def get_connection(
    connection_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> BrokerConnectionSchema:
    service = BrokerConnectionService(session)
    return _schema(service, await service.get(user.id, connection_id))


@router.put("/connections/{connection_id}", response_model=BrokerConnectionSchema)
async def update_connection(
    connection_id: uuid.UUID,
    payload: BrokerConnectionUpdateRequest,
    session: DbSession,
    user: CurrentUser,
) -> BrokerConnectionSchema:
    service = BrokerConnectionService(session)
    row = await service.get(user.id, connection_id)
    row = await service.update(
        row,
        account_external_id=payload.account_external_id,
        api_key=payload.api_key,
        api_secret=payload.api_secret,
        access_token=payload.access_token,
        enabled=payload.enabled,
    )
    return _schema(service, row)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    connection_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> None:
    service = BrokerConnectionService(session)
    row = await service.get(user.id, connection_id)
    await service.delete(user.id, row)


@router.post("/connections/{connection_id}/test", response_model=BrokerConnectionTestResponse)
async def test_connection(
    connection_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> BrokerConnectionTestResponse:
    service = BrokerConnectionService(session)
    row = await service.get(user.id, connection_id)
    ok, status_value, detail = await service.test(row)
    return BrokerConnectionTestResponse(ok=ok, status=status_value, detail=detail)


@router.post("/connections/{connection_id}/activate", response_model=BrokerConnectionSchema)
async def activate_connection(
    connection_id: uuid.UUID, session: DbSession, user: CurrentUser
) -> BrokerConnectionSchema:
    service = BrokerConnectionService(session)
    row = await service.get(user.id, connection_id)
    row = await service.activate(user.id, row)
    return _schema(service, row)
