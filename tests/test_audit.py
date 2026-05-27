"""Admin audit: startup, deploy detection."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from getsync.audit import record_startup
from getsync.config import get_settings
from getsync.state.store import Store
from helpers import isolated_env


class TestAuditStartup(unittest.TestCase):
    def test_app_started_on_every_boot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            with isolated_env(data.parent):
                get_settings.cache_clear()
                store = Store(get_settings().db_path)
                with patch("getsync.audit.deploy_number", return_value=5), patch(
                    "getsync.audit.git_commit_short", return_value="abc1234"
                ), patch("getsync.audit.deployed_at_iso", return_value=None):
                    record_startup(store, data)
                rows = store.list_admin_log(limit=10)
                started = [r for r in rows if r.event_type == "app_started"]
                self.assertEqual(len(started), 1)
                self.assertIn("deploy #5", started[0].message or "")

    def test_deploy_logged_when_metadata_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            state = data / "app_audit_state.json"
            state.parent.mkdir(parents=True)
            state.write_text(
                json.dumps({"deploy_number": 1, "commit": "aaa1111"}),
                encoding="utf-8",
            )
            with isolated_env(data.parent):
                get_settings.cache_clear()
                store = Store(get_settings().db_path)
                with patch("getsync.audit.deploy_number", return_value=2), patch(
                    "getsync.audit.git_commit_short", return_value="bbb2222"
                ), patch("getsync.audit.deployed_at_iso", return_value="2026-01-01T00:00:00Z"):
                    record_startup(store, data)
                deploys = [r for r in store.list_admin_log(limit=20) if r.event_type == "deploy"]
                self.assertEqual(len(deploys), 1)
                self.assertIn("bbb2222", deploys[0].message or "")
                self.assertIn("was", deploys[0].message or "")


if __name__ == "__main__":
    unittest.main()
