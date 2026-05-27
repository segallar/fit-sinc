"""Admin App Health metrics (no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from getsync import __version__
from getsync.config import get_settings
from getsync.ops.app_health import (
    build_admin_health_context,
    format_bytes,
    scan_fit_storage,
    sqlite_file_sizes,
)
from getsync.state.store import Store
from helpers import isolated_env


class TestAppHealthMetrics(unittest.TestCase):
    def test_format_bytes(self) -> None:
        self.assertEqual(format_bytes(500), "500 B")
        self.assertIn("KB", format_bytes(2048))
        self.assertIn("MB", format_bytes(5 * 1024 * 1024))

    def test_scan_fit_storage_counts_fit_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fit_dir = root / "users" / "default" / "activities" / "hammerhead"
            fit_dir.mkdir(parents=True)
            (fit_dir / "ride.fit").write_bytes(b"x" * 100)
            summary = scan_fit_storage(root, users=[("default", "default")])
            self.assertEqual(summary.fit_count, 1)
            self.assertEqual(summary.total_bytes, 100)
            self.assertEqual(len(summary.users), 1)
            self.assertEqual(summary.users[0].slug, "default")

    def test_admin_health_context_with_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                get_settings.cache_clear()
                settings = get_settings()
                store = Store(settings.db_path)
                store.ensure_default_user(password="secret123")
                ctx = build_admin_health_context(settings, store)
                self.assertEqual(ctx["health_status"], "ok")
                self.assertEqual(ctx["health_version"], __version__)
                self.assertGreaterEqual(ctx["health_user_count"], 1)
                self.assertIn("users", ctx["health_table_counts"])
                db_files = ctx["health_db_files"]
                self.assertTrue(any(f.label == "getsync.db" and f.exists for f in db_files))


if __name__ == "__main__":
    unittest.main()
