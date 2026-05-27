"""WebSocket fan-out for live UI updates (per tenant)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

logger = logging.getLogger("getsync.web.realtime")

_hub: "RealtimeHub | None" = None


class RealtimeHub:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._sockets: dict[str, set[WebSocket]] = {}
        self._admin_sockets: set[WebSocket] = set()

    async def connect(
        self,
        user_id: str,
        websocket: WebSocket,
        *,
        is_admin: bool = False,
    ) -> None:
        await websocket.accept()
        async with self._lock:
            self._sockets.setdefault(user_id, set()).add(websocket)
            if is_admin:
                self._admin_sockets.add(websocket)
        logger.debug(
            "ws connected user=%s admin=%s (clients=%d)",
            user_id,
            is_admin,
            len(self._sockets.get(user_id, ())),
        )

    async def disconnect(
        self,
        user_id: str,
        websocket: WebSocket,
        *,
        is_admin: bool = False,
    ) -> None:
        async with self._lock:
            peers = self._sockets.get(user_id)
            if peers:
                peers.discard(websocket)
                if not peers:
                    self._sockets.pop(user_id, None)
            if is_admin:
                self._admin_sockets.discard(websocket)
        logger.debug("ws disconnected user=%s", user_id)

    async def broadcast_admin(self, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._admin_sockets)
        await self._send_many(targets, payload)

    async def broadcast(self, user_id: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._sockets.get(user_id, ()))
        await self._send_many(targets, payload, user_id=user_id)

    async def _send_many(
        self,
        targets: list[WebSocket],
        payload: dict[str, Any],
        *,
        user_id: str | None = None,
    ) -> None:
        if not targets:
            return
        text = json.dumps(payload, separators=(",", ":"))
        dead: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        if not dead:
            return
        async with self._lock:
            if user_id is not None:
                peers = self._sockets.get(user_id)
                if peers:
                    for ws in dead:
                        peers.discard(ws)
                    if not peers:
                        self._sockets.pop(user_id, None)
            for ws in dead:
                self._admin_sockets.discard(ws)

    async def run_session(
        self,
        user_id: str,
        websocket: WebSocket,
        *,
        is_admin: bool = False,
    ) -> None:
        await self.connect(user_id, websocket, is_admin=is_admin)
        try:
            while True:
                raw = await websocket.receive_text()
                if raw.strip().lower() == "ping":
                    await websocket.send_text('{"type":"pong"}')
        except WebSocketDisconnect:
            pass
        finally:
            await self.disconnect(user_id, websocket, is_admin=is_admin)


def get_hub() -> RealtimeHub:
    global _hub
    if _hub is None:
        _hub = RealtimeHub()
    return _hub


def reset_hub() -> None:
    """Tests: drop connections between cases."""
    global _hub
    _hub = None


async def notify_activity_updated(
    user_id: str,
    activity_id: str,
    sync_status: str,
) -> None:
    await get_hub().broadcast(
        user_id,
        {
            "type": "activity_updated",
            "activity_id": activity_id,
            "sync_status": sync_status,
        },
    )


async def notify_admin_log_refresh() -> None:
    await get_hub().broadcast_admin({"type": "admin_log_refresh"})


async def notify_admin_health_refresh() -> None:
    await get_hub().broadcast_admin({"type": "admin_health_refresh"})
