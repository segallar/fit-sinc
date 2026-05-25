"""SQLite v1 → v2 schema migration (no network)."""

import tempfile
import unittest
from pathlib import Path

import sqlite3

from fit_sinc.state.store import Store


def _create_v1_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE activities (
            activity_id TEXT PRIMARY KEY,
            name TEXT,
            activity_date TEXT,
            distance REAL,
            duration REAL,
            sync_status TEXT NOT NULL DEFAULT 'pending',
            fit_path TEXT,
            garmin_result TEXT,
            synced_at TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        INSERT INTO activities (
            activity_id, name, sync_status, created_at, updated_at
        ) VALUES ('act-1', 'Ride', 'synced', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z');

        CREATE TABLE sync_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_id TEXT,
            event_type TEXT NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        );
        INSERT INTO sync_events (activity_id, event_type, created_at)
        VALUES ('act-1', 'synced', '2026-01-01T00:00:00Z');
        """
    )
    conn.commit()
    conn.close()


class TestStoreV1Migration(unittest.TestCase):
    def test_opens_legacy_db_without_user_id_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "legacy.db"
            _create_v1_db(db)
            store = Store(db)
            store.ensure_default_user(password="test")
            self.assertTrue(store.is_synced("default", "act-1"))
            events = store.list_events(user_id="default", limit=10)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].user_id, "default")


if __name__ == "__main__":
    unittest.main()
