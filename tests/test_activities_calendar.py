"""Activity month calendar aggregation."""

import unittest

from getsync.activities.calendar import (
    aggregate_days_by_local_date,
    build_activity_calendar,
)
from getsync.state.store import Store


class TestActivityCalendar(unittest.TestCase):
    def test_aggregate_worst_status(self) -> None:
        rows = [
            ("2026-05-10T08:00:00+00:00", "synced"),
            ("2026-05-10T18:00:00+00:00", "error"),
            ("2026-05-11T10:00:00+00:00", "pending"),
        ]
        stats = aggregate_days_by_local_date(
            rows, display_tz="UTC", year=2026, month=5
        )
        self.assertEqual(stats["2026-05-10"].count, 2)
        self.assertEqual(stats["2026-05-10"].worst_status, "error")
        self.assertEqual(stats["2026-05-11"].count, 1)

    def test_build_calendar_links_and_navigation(self) -> None:
        import tempfile
        from pathlib import Path

        from getsync.config import get_settings

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cal.db"
            store = Store(db)
            user = store.create_user(
                slug="cal",
                display_name="Cal",
                email="cal@example.com",
                password="secretpass123",
                timezone="UTC",
            )
            store.upsert_activity(
                user.id,
                "a1",
                name="Ride",
                activity_date="2026-05-15T10:00:00+00:00",
                sync_status="synced",
                source="hammerhead",
            )

            view = build_activity_calendar(
                store,
                user.id,
                year=2026,
                month=5,
                display_tz="UTC",
                prev_href="/prev",
                next_href="/next",
                today_href="/today",
                day_list_href=lambda d: f"/list?date={d}",
            )
            self.assertEqual(view.month_label, "May 2026")
            self.assertEqual(view.prev_href, "/prev")
            self.assertGreater(view.total_in_month, 0)
            found = False
            for week in view.weeks:
                for cell in week:
                    if cell.iso == "2026-05-15":
                        found = True
                        self.assertEqual(cell.count, 1)
                        self.assertEqual(cell.list_href, "/list?date=2026-05-15")
            self.assertTrue(found)


if __name__ == "__main__":
    unittest.main()
