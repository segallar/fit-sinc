"""WebSocket realtime hub."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from getsync.config import get_settings
from getsync.state.store import Store
from getsync.web.realtime import (
    RealtimeHub,
    notify_activity_updated,
    notify_admin_log_refresh,
    reset_hub,
)
from helpers import isolated_env


class TestRealtimeHub(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        reset_hub()

    async def test_broadcast_reaches_connected_socket(self) -> None:
        hub = RealtimeHub()
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        await hub.connect("default", ws)
        await hub.broadcast("default", {"type": "activity_updated", "activity_id": "a1"})
        ws.send_text.assert_awaited()
        payload = ws.send_text.await_args.args[0]
        self.assertIn("activity_updated", payload)

    async def test_admin_broadcast_only_to_admin_sockets(self) -> None:
        hub = RealtimeHub()
        admin_ws = AsyncMock()
        admin_ws.send_text = AsyncMock()
        user_ws = AsyncMock()
        user_ws.send_text = AsyncMock()
        await hub.connect("admin1", admin_ws, is_admin=True)
        await hub.connect("user2", user_ws, is_admin=False)
        from getsync.web import realtime as rt

        rt._hub = hub
        await notify_admin_log_refresh()
        admin_ws.send_text.assert_awaited()
        user_ws.send_text.assert_not_awaited()

    async def test_notify_activity_updated_payload(self) -> None:
        hub = RealtimeHub()
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        await hub.connect("user1", ws)
        from getsync.web import realtime as rt

        rt._hub = hub
        await notify_activity_updated("user1", "act-9", "synced")
        text = ws.send_text.await_args.args[0]
        self.assertIn('"sync_status":"synced"', text.replace(" ", ""))


class TestRealtimeWebSocketAuth(unittest.TestCase):
    def tearDown(self) -> None:
        reset_hub()
        get_settings.cache_clear()

    def test_ws_requires_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                get_settings.cache_clear()
                from getsync.web.app import app

                client = TestClient(app)
                with self.assertRaises(Exception):
                    with client.websocket_connect("/app/ws"):
                        pass


if __name__ == "__main__":
    unittest.main()
