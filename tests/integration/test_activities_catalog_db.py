"""Activity catalog in SQLite (multi-source)."""

import tempfile
import unittest
from pathlib import Path

from getsync.activities.browse import ActivityBrowseRow
from getsync.activities.catalog import persist_browse_rows
from getsync.state.store import Store
from helpers import isolated_env


class TestActivitiesCatalogDb(unittest.TestCase):
    def test_upsert_hammerhead_and_garmin_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.config import get_settings

                store = Store(get_settings().db_path)
                store.ensure_default_user(password="test")
                uid = "default"

                persist_browse_rows(
                    store,
                    uid,
                    [
                        ActivityBrowseRow(
                            source="hammerhead",
                            external_id="hh-1",
                            name="Ride",
                            activity_date="2025-06-01T10:00:00Z",
                            distance=10.0,
                            duration=3600.0,
                            activity_type="cycling",
                            sync_status="synced",
                            sync_detail=None,
                            hammerhead_id="hh-1",
                            garmin_id=42,
                            fit_available=True,
                        ),
                        ActivityBrowseRow(
                            source="garmin",
                            external_id="99",
                            name="Run",
                            activity_date="2025-06-02T10:00:00Z",
                            distance=5.0,
                            duration=1800.0,
                            activity_type="running",
                            sync_status="not synced",
                            sync_detail=None,
                            hammerhead_id=None,
                            garmin_id=99,
                            fit_available=False,
                        ),
                    ],
                )

                self.assertEqual(store.count_catalog(uid), 2)
                hh = store.get_activity(uid, "hh-1", source="hammerhead")
                self.assertIsNotNone(hh)
                assert hh is not None
                self.assertEqual(hh.source, "hammerhead")
                self.assertEqual(hh.activity_type, "cycling")

                gm = store.get_activity(uid, "99", source="garmin")
                self.assertIsNotNone(gm)
                assert gm is not None
                self.assertEqual(gm.source, "garmin")

                index = store.build_sync_index(uid)
                self.assertIn("hh-1", index)
                self.assertEqual(index["hh-1"].sync_status, "synced")

    def test_source_column_migration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "legacy.db"
            import sqlite3

            conn = sqlite3.connect(db)
            conn.execute(
                """
                CREATE TABLE activities (
                    user_id TEXT NOT NULL,
                    activity_id TEXT NOT NULL,
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
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, activity_id)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO activities (
                    user_id, activity_id, name, sync_status, created_at, updated_at
                ) VALUES ('default', 'act-1', 'Ride', 'synced', '2026-01-01', '2026-01-01')
                """
            )
            conn.commit()
            conn.close()

            store = Store(db)
            row = store.get_activity("default", "act-1", source="hammerhead")
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.source, "hammerhead")


if __name__ == "__main__":
    unittest.main()
