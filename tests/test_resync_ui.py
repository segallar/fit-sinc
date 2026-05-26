"""Re-sync UI in /app (no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from getsync.state.store import Store
from helpers import isolated_env


class TestResyncUi(unittest.TestCase):
    def _setup_client(self, tmp: str) -> tuple[TestClient, Store, str]:
        settings = __import__(
            "getsync.config", fromlist=["get_settings"]
        ).get_settings()
        store = Store(settings.db_path)
        store.ensure_default_user(email="u@test.local", password="pass")
        store.upsert_activity(
            settings.default_user_id,
            "act-err",
            name="Failed ride",
            sync_status="pending",
        )
        store.mark_error(settings.default_user_id, "act-err", "test failure")
        store.upsert_activity(
            settings.default_user_id,
            "act-ok",
            name="OK ride",
            sync_status="synced",
        )
        from getsync.web.app import app

        client = TestClient(app)
        client.post(
            "/app/login",
            data={"email": "u@test.local", "password": "pass"},
            follow_redirects=False,
        )
        return client, store, settings.default_user_id

    @patch("getsync.web.app_routes._run_sync_force", new_callable=AsyncMock)
    def test_retry_redirects_to_next(self, _mock_sync: AsyncMock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, _, _ = self._setup_client(tmp)
                r = client.post(
                    "/app/activities/act-err/retry",
                    data={"next": "/app/activities?status=error"},
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                loc = r.headers.get("location", "")
                self.assertIn("status=error", loc)

    @patch("getsync.web.app_routes._run_sync_force", new_callable=AsyncMock)
    def test_retry_all_errors_queues_and_redirects(self, _mock_sync: AsyncMock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store, user_id = self._setup_client(tmp)
                failed = store.list_activities(user_id, limit=50, sync_status="error")
                self.assertEqual(len(failed), 1)
                r = client.post(
                    "/app/activities/retry-errors",
                    data={"next": ""},
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertIn("queued=1", r.headers.get("location", ""))
                events = store.list_events(limit=10, user_id=user_id)
                types = [e.event_type for e in events]
                self.assertIn("resync_queued", types)
                self.assertEqual(_mock_sync.await_count, 1)


if __name__ == "__main__":
    unittest.main()
