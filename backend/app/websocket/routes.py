"""Authenticated realtime WebSocket endpoint.

A single endpoint at ``/ws``; clients authenticate with a short-lived access
token. The server sends periodic heartbeat frames and answers ``ping`` with
``pong``. Domain events are delivered as typed envelopes
``{event, event_id, timestamp, version, data}``.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi import status as ws_status

from app.core.config import get_settings
from app.core.logging import get_logger
from app.realtime.publisher import get_connection_manager
from app.websocket.auth import authenticate_ws_token

logger = get_logger(__name__)

router = APIRouter()


def _envelope(event: str, data: dict) -> dict:
    return {
        "event": event,
        "event_id": uuid.uuid4().hex,
        "timestamp": datetime.now(UTC).isoformat(),
        "version": 1,
        "data": data,
    }


async def _heartbeat_loop(websocket: WebSocket, user_id: uuid.UUID, interval: int) -> None:
    stop = asyncio.Event()
    heartbeat = asyncio.create_task(_send_heartbeats(websocket, user_id, interval, stop))
    try:
        while True:
            raw = await websocket.receive_text()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except ValueError:
                continue
            if isinstance(payload, dict) and payload.get("event") == "ping":
                await websocket.send_json(_envelope("pong", {"user_id": str(user_id)}))
    finally:
        stop.set()
        heartbeat.cancel()


async def _send_heartbeats(
    websocket: WebSocket, user_id: uuid.UUID, interval: int, stop: asyncio.Event
) -> None:
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
            return
        except TimeoutError:
            try:
                await websocket.send_json(_envelope("heartbeat", {"user_id": str(user_id)}))
            except Exception:  # noqa: BLE001 - peer gone; receive loop will clean up
                return


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    settings = get_settings()
    candidate = token
    if not candidate:
        header = websocket.headers.get("authorization")
        if header and header.lower().startswith("bearer "):
            candidate = header[7:]

    user_id = authenticate_ws_token(candidate, settings)
    if user_id is None:
        await websocket.close(code=ws_status.WS_1008_POLICY_VIOLATION)
        return

    manager = get_connection_manager()
    if not await manager.connect(user_id, websocket):
        return
    logger.info("websocket_connected", user_id=str(user_id))
    try:
        await _heartbeat_loop(websocket, user_id, max(1, settings.WEBSOCKET_HEARTBEAT_SECONDS))
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, websocket)
        logger.info("websocket_disconnected", user_id=str(user_id))
