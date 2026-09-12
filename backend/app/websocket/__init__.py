"""WebSocket layer (Phase 4).

Authentication, the typed event envelope and the connection registry live here
and in :mod:`app.realtime`. Domain services never import this module.
"""

from app.websocket.auth import authenticate_ws_token
from app.websocket.routes import router as websocket_router

__all__ = ["authenticate_ws_token", "websocket_router"]
