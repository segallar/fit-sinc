"""Activity month calendar aggregation."""

import tempfile
import unittest
from pathlib import Path

from getsync.activities.browse import (
    ActivityBrowseRow,
    ActivityFilters,
    _dedupe_linked_rows,
    _matches_filters,
    _sort_rows_by_date,
    catalog_row_to_browse_row,
    resolve_activity_filters,
)
from getsync.activities.calendar import (
    aggregate_days_by_local_date,
    attach_calendar_row_views,
    build_activity_calendar,
    format_activity_chip_name,
)
from getsync.catalog.infra.store_catalog import StoreCatalog
from getsync.contracts.activities import NormalizedActivity
from getsync.state.store import Store
from getsync.users.context import UserContext
from getsync.config import get_settings


class TestActivityCalendar(unittest.TestCase):
    def test_format_activity_chip_name(self) -> None:
        self.assertEqual(
            format_activity_chip_name(
                "Рузский район Бег",
                "2026-05-02T08:55:00+00:00",
                display_tz="Europe/Moscow",
            ),
            "11:55 Рузский район Бег",
        )
        self.assertEqual(
            format_activity_chip_name("Ride", None, display_tz="UTC"),
            "Ride",
        )

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

    def test_build_calendar_activities_and_menu_rows(self) -> None:
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
                name="Morning Ride",
                activity_date="2026-05-15T10:00:00+00:00",
                sync_status="synced",
                source="hammerhead",
            )
            store.upsert_activity(
                user.id,
                "g1",
                name="Evening Run",
                activity_date="2026-05-15T18:00:00+00:00",
                sync_status="not synced",
                source="garmin",
            )

            view = build_activity_calendar(
                ctx=UserContext(user.id, get_settings()),
                catalog=StoreCatalog(store),
                year=2026,
                month=5,
                display_tz="UTC",
                prev_href="/prev",
                next_href="/next",
                today_href="/today",
                day_list_href=lambda d: f"/list?date={d}",
            )
            self.assertEqual(view.month_label, "May 2026")
            self.assertEqual(view.total_in_month, 2)

            day_cell = None
            for week in view.weeks:
                for cell in week:
                    if cell.iso == "2026-05-15":
                        day_cell = cell
                        break
            self.assertIsNotNone(day_cell)
            assert day_cell is not None
            self.assertEqual(day_cell.count, 2)
            self.assertEqual(day_cell.list_href, "/list?date=2026-05-15")
            self.assertEqual(len(day_cell.activities), 2)
            names = {a.name for a in day_cell.activities}
            self.assertEqual(names, {"Morning Ride", "Evening Run"})

            rendered = attach_calendar_row_views(
                view,
                lambda row: {
                    "name": format_activity_chip_name(
                        row.name, row.activity_date, display_tz="UTC"
                    ),
                    "source": row.source,
                },
            )
            rendered_day = None
            for week in rendered.weeks:
                for cell in week:
                    if cell.iso == "2026-05-15":
                        rendered_day = cell
                        break
            assert rendered_day is not None
            self.assertEqual(len(rendered_day.activity_rows), 2)
            chip_names = {r["name"] for r in rendered_day.activity_rows}
            self.assertEqual(
                chip_names,
                {"10:00 Morning Ride", "18:00 Evening Run"},
            )

    def test_catalog_rename_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cal.db"
            store = Store(db)
            user = store.create_user(
                slug="mgr",
                display_name="Mgr",
                email="mgr@example.com",
                password="secretpass123",
            )
            store.upsert_activity(
                user.id,
                "hh-1",
                source="hammerhead",
                name="Old",
                storage_key="activities/hammerhead/hh-1.fit",
            )
            self.assertTrue(
                store.update_activity_name(
                    user.id, "hh-1", "New name", source="hammerhead"
                )
            )
            row = store.get_activity(user.id, "hh-1", source="hammerhead")
            assert row is not None
            self.assertEqual(row.name, "New name")
            found, key = store.delete_activity(user.id, "hh-1", source="hammerhead")
            self.assertTrue(found)
            self.assertEqual(key, "activities/hammerhead/hh-1.fit")
            self.assertIsNone(
                store.get_activity(user.id, "hh-1", source="hammerhead")
            )

    def test_catalog_row_to_browse_hammerhead_fit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "cal.db"
            store = Store(db)
            user = store.create_user(
                slug="fit",
                display_name="Fit",
                email="fit@example.com",
                password="secretpass123",
            )
            store.upsert_activity(
                user.id,
                "hh-1",
                source="hammerhead",
                name="Ride",
                sync_status="synced",
                storage_key="activities/hammerhead/hh-1.fit",
            )
            row = store.get_activity(user.id, "hh-1", source="hammerhead")
            assert row is not None
            index = store.build_sync_index(user.id)
            normalized = NormalizedActivity(
                user_id=user.id,
                source=row.source,
                activity_id=row.activity_id,
                name=row.name,
                activity_date=row.activity_date,
                distance=row.distance,
                duration=row.duration,
                activity_type=row.activity_type,
                sync_status=row.sync_status,
                storage_key=row.storage_key,
            )
            browse = catalog_row_to_browse_row(normalized, index, {})
            self.assertTrue(browse.fit_available)
            self.assertEqual(browse.hammerhead_id, "hh-1")


if __name__ == "__main__":
    unittest.main()
