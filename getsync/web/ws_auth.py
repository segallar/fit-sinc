"""Resolve logged-in user from WebSocket (session cookie via SessionMiddleware)."""

from __future__ import annotations

from starlette.websockets import WebSocket

from getsync.config import get_settings
from getsync.state.store import Store
from getsync.users.models import UserRow
from getsync.web.auth import SESSION_USER_KEY


def user_from_websocket(websocket: WebSocket) -> UserRow | None:
    session = websocket.scope.get("session")
    if not session:
        return None
    uid = session.get(SESSION_USER_KEY)
    if not uid:
        return None
    user = Store(get_settings().db_path).get_user(str(uid))
    if user is None or user.disabled:
        return None
    return user


def user_id_from_websocket(websocket: WebSocket) -> str | None:
    user = user_from_websocket(websocket)
    return user.id if user else None
