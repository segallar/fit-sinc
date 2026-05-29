"""Unified activities browse (multi-source catalog)."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from getsync.activities.browse import (
    ActivityBrowseRow,
    ActivityFilters,
    _dedupe_linked_rows,
    _matches_filters,
    _sort_rows_by_date,
    catalog_row_to_browse_row,
    resolve_activity_filters,
)
from getsync.workspace.domain.filters import activity_type_matches
from getsync.contracts.activities import NormalizedActivity
from getsync.state.store import Store
from helpers import isolated_env


class TestActivitiesBrowse(unittest.TestCase):
    def test_resolve_activity_filters_defaults_to_month(self) -> None:
        empty = ActivityFilters()
        eff = resolve_activity_filters(
            empty,
            view="list",
            year=2026,
            month=5,
            today=date(2026, 5, 15),
        )
        self.assertEqual(eff.date_from, "2026-05-01")
        self.assertEqual(eff.date_to, "2026-05-31")

        explicit = ActivityFilters(date_from="2026-04-01", date_to="2026-04-30")
        self.assertEqual(
            resolve_activity_filters(
                explicit,
                view="list",
                year=2026,
                month=5,
                today=date(2026, 5, 15),
            ),
            explicit,
        )

    def test_dedupe_linked_rows(self) -> None:
        hh = ActivityBrowseRow(
            source="hammerhead",
            external_id="hh1",
            name="Ride",
            activity_date="2025-06-01T10:00:00Z",
            distance=10.0,
            duration=3600.0,
            activity_type="ride",
            sync_status="synced",
            sync_detail=None,
            hammerhead_id="hh1",
            garmin_id=99,
            fit_available=True,
        )
        gm_dup = ActivityBrowseRow(
            source="garmin",
            external_id="99",
            name="Ride",
            activity_date="2025-06-01T10:00:00Z",
            distance=10.0,
            duration=3600.0,
            activity_type="ride",
            sync_status="synced",
            sync_detail=None,
            hammerhead_id="hh1",
            garmin_id=99,
            fit_available=True,
        )
        gm_only = ActivityBrowseRow(
            source="garmin",
            external_id="100",
            name="Run",
            activity_date="2025-06-02T10:00:00Z",
            distance=5.0,
            duration=1800.0,
            activity_type="run",
            sync_status="not synced",
            sync_detail=None,
            hammerhead_id=None,
            garmin_id=100,
            fit_available=False,
        )
        out = _dedupe_linked_rows([hh, gm_dup, gm_only])
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].source, "hammerhead")
        self.assertEqual(out[1].garmin_id, 100)

    def test_dedupe_linked_rows_keeps_strava(self) -> None:
        strava = ActivityBrowseRow(
            source="strava",
            external_id="sv1",
            name="Morning Run",
            activity_date="2026-05-28T09:41:52Z",
            distance=5.0,
            duration=1800.0,
            activity_type="run",
            sync_status="not synced",
            sync_detail=None,
            hammerhead_id=None,
            garmin_id=None,
            fit_available=False,
        )
        hh = ActivityBrowseRow(
            source="hammerhead",
            external_id="hh1",
            name="Ride",
            activity_date="2025-06-01T10:00:00Z",
            distance=10.0,
            duration=3600.0,
            activity_type="ride",
            sync_status="synced",
            sync_detail=None,
            hammerhead_id="hh1",
            garmin_id=None,
            fit_available=True,
        )
        out = _dedupe_linked_rows([hh, strava])
        self.assertEqual(len(out), 2)
        sources = {row.source for row in out}
        self.assertEqual(sources, {"hammerhead", "strava"})

    def test_normalized_to_browse_row_keeps_strava_source(self) -> None:
        row = NormalizedActivity(
            user_id="u1",
            source="strava",
            activity_id="18685363629",
            name="Morning Run",
            activity_date="2026-05-28T09:41:52Z",
            distance=5000.0,
            duration=1800.0,
            activity_type="Run",
            sync_status="not synced",
            storage_key=None,
        )
        browse = catalog_row_to_browse_row(row, {}, {})
        self.assertEqual(browse.source, "strava")
        self.assertEqual(browse.external_id, "18685363629")
        self.assertIsNone(browse.garmin_id)

    def test_activity_type_matches_strava_sport_types(self) -> None:
        self.assertTrue(activity_type_matches("running", "Run"))
        self.assertTrue(activity_type_matches("cycling", "Ride"))
        self.assertTrue(activity_type_matches("cycling", "VirtualRide"))
        self.assertTrue(activity_type_matches("swimming", "Swim"))
        self.assertFalse(activity_type_matches("cycling", "Run"))

    def test_source_filter_on_row(self) -> None:
        row = ActivityBrowseRow(
            source="garmin",
            external_id="1",
            name="x",
            activity_date=None,
            distance=None,
            duration=None,
            activity_type=None,
            sync_status="not synced",
            sync_detail=None,
            hammerhead_id=None,
            garmin_id=1,
            fit_available=False,
        )
        self.assertFalse(
            _matches_filters(row, ActivityFilters(source="hammerhead"), display_tz="UTC")
        )
        self.assertTrue(
            _matches_filters(row, ActivityFilters(source="garmin"), display_tz="UTC")
        )

    def test_sort_rows_by_date_desc(self) -> None:
        rows = [
            ActivityBrowseRow(
                source="hammerhead",
                external_id="a",
                name="old",
                activity_date="2025-01-01T00:00:00Z",
                distance=None,
                duration=None,
                activity_type=None,
                sync_status="not synced",
                sync_detail=None,
                hammerhead_id="a",
                garmin_id=None,
                fit_available=False,
            ),
            ActivityBrowseRow(
                source="garmin",
                external_id="b",
                name="new",
                activity_date="2025-06-01T00:00:00Z",
                distance=None,
                duration=None,
                activity_type=None,
                sync_status="not synced",
                sync_detail=None,
                hammerhead_id=None,
                garmin_id=2,
                fit_available=False,
            ),
        ]
        sorted_rows = _sort_rows_by_date(rows, display_tz="UTC")
        self.assertEqual(sorted_rows[0].name, "new")

    @patch("getsync.catalog.application.refresh.refresh_from_providers")
    def test_fetch_all_sources_merges(self, mock_refresh: MagicMock) -> None:
        import asyncio

        from getsync.activities.browse import fetch_activities_page
        from getsync.activities.catalog import persist_browse_rows
        from getsync.catalog.infra.store_catalog import StoreCatalog
        from getsync.config import get_settings
        from getsync.users.context import UserContext

        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                ctx = UserContext(user_id="u1", settings=get_settings())
                store = Store(get_settings().db_path)
                catalog = StoreCatalog(store)
                persist_browse_rows(
                    store,
                    "u1",
                    [
                        ActivityBrowseRow(
                            source="hammerhead",
                            external_id="h1",
                            name="HH",
                            activity_date="2025-06-01T00:00:00Z",
                            distance=None,
                            duration=None,
                            activity_type=None,
                            sync_status="not synced",
                            sync_detail=None,
                            hammerhead_id="h1",
                            garmin_id=None,
                            fit_available=False,
                        ),
                        ActivityBrowseRow(
                            source="garmin",
                            external_id="g1",
                            name="GM",
                            activity_date="2025-06-02T00:00:00Z",
                            distance=None,
                            duration=None,
                            activity_type=None,
                            sync_status="not synced",
                            sync_detail=None,
                            hammerhead_id=None,
                            garmin_id=1,
                            fit_available=False,
                        ),
                    ],
                )
                page = asyncio.run(
                    fetch_activities_page(
                        filters=ActivityFilters(),
                        ctx=ctx,
                        catalog=catalog,
                    )
                )
        self.assertEqual(page.mode, "all")
        self.assertEqual(len(page.rows), 2)
        self.assertEqual(page.rows[0].name, "GM")
        mock_refresh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
