"""WebSocket endpoints under /app."""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketException, status

from getsync.web.realtime import get_hub
from getsync.web.ws_auth import user_from_websocket

logger = logging.getLogger("getsync.web.ws")

router = APIRouter(prefix="/app", tags=["websocket"])


@router.websocket("/ws")
async def app_realtime_socket(websocket: WebSocket) -> None:
    user = user_from_websocket(websocket)
    if not user:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    try:
        await get_hub().run_session(
            user.id, websocket, is_admin=user.is_admin
        )
    except WebSocketException:
        raise
    except Exception:
        logger.exception("websocket session ended with error user=%s", user.id)
