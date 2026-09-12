"""WebSocket connection registry and best-effort delivery."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

MAX_CONNECTIONS_PER_USER = 5


class ConnectionManager:
    """Tracks live WebSocket connections per user.

    Delivery is best-effort: a failure to send to one client is logged and never
    propagates to the domain operation that produced the event.
    """

    def __init__(self) -> None:
        self._connections: dict[str, set[Any]] = {}

    @property
    def connection_count(self) -> int:
        return sum(len(sockets) for sockets in self._connections.values())

    @property
    def user_count(self) -> int:
        return len(self._connections)

    async def connect(self, user_id: uuid.UUID, websocket: Any) -> bool:
        key = str(user_id)
        sockets = self._connections.setdefault(key, set())
        if len(sockets) >= MAX_CONNECTIONS_PER_USER:
            await websocket.close(code=1013, reason="Too many connections")
            return False
        await websocket.accept()
        sockets.add(websocket)
        return True

    def disconnect(self, user_id: uuid.UUID, websocket: Any) -> None:
        key = str(user_id)
        sockets = self._connections.get(key)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._connections.pop(key, None)

    async def send_to_user(self, user_id: uuid.UUID, payload: dict[str, Any]) -> int:
        sockets = list(self._connections.get(str(user_id), ()))
        return await self._send(sockets, payload)

    async def broadcast(self, payload: dict[str, Any]) -> int:
        sockets = [socket for group in self._connections.values() for socket in group]
        return await self._send(sockets, payload)

    async def _send(self, sockets: list[Any], payload: dict[str, Any]) -> int:
        delivered = 0
        for websocket in sockets:
            try:
                await websocket.send_json(payload)
                delivered += 1
            except Exception as exc:  # noqa: BLE001 - delivery is best-effort
                logger.warning("websocket_send_failed", error=str(exc))
        return delivered
