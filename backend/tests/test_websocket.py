"""WebSocket connection manager, authentication and endpoint tests."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from app.core.config import get_settings
from app.core.security import create_access_token
from app.main import app
from app.realtime.bus import ConnectionManager
from app.websocket.auth import authenticate_ws_token
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


class FakeSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.sent: list[dict[str, Any]] = []
        self.closed = False

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, payload: dict[str, Any]) -> None:
        self.sent.append(payload)

    async def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.closed = True


async def test_manager_connect_broadcast_disconnect() -> None:
    manager = ConnectionManager()
    socket = FakeSocket()
    user_id = uuid.uuid4()

    assert await manager.connect(user_id, socket) is True
    assert socket.accepted is True
    assert manager.connection_count == 1

    await manager.send_to_user(user_id, {"event": "targeted"})
    await manager.broadcast({"event": "broadcast"})
    assert [item["event"] for item in socket.sent] == ["targeted", "broadcast"]

    manager.disconnect(user_id, socket)
    assert manager.connection_count == 0
    assert manager.user_count == 0


async def test_manager_limits_connections_per_user() -> None:
    from app.realtime.bus import MAX_CONNECTIONS_PER_USER

    manager = ConnectionManager()
    user_id = uuid.uuid4()
    sockets = [FakeSocket() for _ in range(MAX_CONNECTIONS_PER_USER)]
    for socket in sockets:
        assert await manager.connect(user_id, socket) is True

    overflow = FakeSocket()
    assert await manager.connect(user_id, overflow) is False
    assert overflow.closed is True
    assert manager.connection_count == MAX_CONNECTIONS_PER_USER


def test_authenticate_ws_token() -> None:
    settings = get_settings()
    valid = create_access_token(str(uuid.uuid4()), settings)
    assert authenticate_ws_token(valid, settings) is not None
    assert authenticate_ws_token(None, settings) is None
    assert authenticate_ws_token("not-a-token", settings) is None


def test_websocket_rejects_unauthorized() -> None:
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_text()


def test_websocket_ping_pong() -> None:
    settings = get_settings()
    token = create_access_token(str(uuid.uuid4()), settings)
    client = TestClient(app)
    with client.websocket_connect(f"/ws?token={token}") as websocket:
        websocket.send_json({"event": "ping"})
        message = websocket.receive_json()
        assert message["event"] == "pong"
        assert message["version"] == 1
        assert message["event_id"]
        assert message["timestamp"]
