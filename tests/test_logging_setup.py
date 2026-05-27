"""Rotating file logging and audit mirror from store.log_event."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from getsync.config import get_settings
from getsync.logging_setup import configure_logging, reset_logging_for_tests
from getsync.state.store import Store
from helpers import isolated_env


class TestLoggingSetup(unittest.TestCase):
    def tearDown(self) -> None:
        get_settings.cache_clear()
        reset_logging_for_tests()

    def test_log_file_receives_sync_audit_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                get_settings.cache_clear()
                configure_logging(force=True)
                settings = get_settings()
                log_path = settings.resolved_log_file
                self.assertIsNotNone(log_path)
                assert log_path is not None

                store = Store(settings.db_path)
                store.ensure_default_user(password="x")
                store.log_event(
                    "webhook_received",
                    "hammerheadUserId=1",
                    "act-log-test",
                    user_id="default",
                )

                self.assertTrue(log_path.is_file())
                text = log_path.read_text(encoding="utf-8")
                self.assertIn("webhook_received", text)
                self.assertIn("act-log-test", text)
                self.assertIn("getsync.audit", text)


if __name__ == "__main__":
    unittest.main()
