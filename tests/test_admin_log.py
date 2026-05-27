"""Unified admin log (sync + Garmin JWT)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from getsync.config import get_settings
from getsync.state.store import Store
from helpers import isolated_env


class TestAdminLogStore(unittest.TestCase):
    def test_merged_log_sorted_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                get_settings.cache_clear()
                store = Store(get_settings().db_path)
                store.ensure_default_user(password="x")
                store.log_event("webhook_received", "", "act-1", user_id="default")
                store.log_session_refresh("manual", "ok", "jwt ok", user_id="default")
                store.log_event("fit_saved", "key", "act-1", user_id="default")

                rows = store.list_admin_log(limit=10)
                self.assertEqual(len(rows), 3)
                kinds = [r.log_kind for r in rows]
                self.assertIn("sync", kinds)
                self.assertIn("garmin", kinds)
                self.assertGreaterEqual(rows[0].created_at, rows[-1].created_at)

    def test_count_admin_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                get_settings.cache_clear()
                store = Store(get_settings().db_path)
                store.ensure_default_user(password="x")
                store.log_event("sync_started", "", "a", user_id="default")
                store.log_session_refresh("bg", "failed", "x", user_id="default")
                self.assertEqual(store.count_admin_log(), 2)


if __name__ == "__main__":
    unittest.main()
