"""sync_activity idempotency (no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fit_sinc.state.store import Store
from fit_sinc.sync.service import sync_activity
from helpers import isolated_env


class TestSyncActivity(unittest.IsolatedAsyncioTestCase):
    async def test_skips_already_synced_without_api_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "fit_sinc.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.ensure_default_user(password="x")
                store.mark_synced(
                    "default",
                    "act-done",
                    "/tmp/fake.fit",
                    {"id": 1},
                    name="Done ride",
                )

                result = await sync_activity("act-done", user_id="default")
                self.assertEqual(result.status, "skipped")
                self.assertIn("already synced", result.message)

                events = store.list_events(user_id="default", limit=20)
                types = [e.event_type for e in events]
                self.assertIn("skipped", types)
                self.assertNotIn("sync_started", types)


if __name__ == "__main__":
    unittest.main()
