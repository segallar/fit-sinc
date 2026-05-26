"""Date formatting and activity filters in user timezone."""

import unittest

from fit_sinc.activities.browse import ActivityBrowseRow, ActivityFilters, _matches_filters
from fit_sinc.timeutil import format_datetime_parts, format_iso, parse_date_only
from fit_sinc.web.html import make_formatter
from fit_sinc.web.templating import render_template


class TestTimeutil(unittest.TestCase):
    def test_format_iso_uses_user_timezone(self) -> None:
        iso = "2025-06-15T10:00:00+00:00"
        msk = format_iso(iso, tz="Europe/Moscow")
        berlin = format_iso(iso, tz="Europe/Berlin")
        self.assertEqual(msk, "2025-06-15 13:00")
        self.assertEqual(berlin, "2025-06-15 12:00")

    def test_datetime_parts_differ_by_tz(self) -> None:
        iso = "2025-01-01T22:30:00+00:00"
        msk_date, msk_time = format_datetime_parts(iso, tz="Europe/Moscow")
        ny_date, ny_time = format_datetime_parts(iso, tz="America/New_York")
        self.assertEqual((msk_date, msk_time), ("02.01.2025", "01:30:00"))
        self.assertEqual((ny_date, ny_time), ("01.01.2025", "17:30:00"))

    def test_date_filter_respects_timezone_boundary(self) -> None:
        row = ActivityBrowseRow(
            source="hammerhead",
            external_id="1",
            name="Ride",
            activity_date="2025-06-01T21:00:00+00:00",
            distance=None,
            duration=None,
            activity_type=None,
            fit_sinc_status="synced",
            fit_sinc_detail=None,
            hammerhead_id="1",
            garmin_id=None,
            fit_available=False,
        )
        filters = ActivityFilters(date_from="2025-06-02")
        self.assertTrue(
            _matches_filters(row, filters, display_tz="Europe/Moscow")
        )
        self.assertFalse(
            _matches_filters(row, filters, display_tz="America/Los_Angeles")
        )

    def test_parse_date_only_midnight_in_tz(self) -> None:
        start = parse_date_only("2025-06-02", tz="Europe/Moscow")
        self.assertIsNotNone(start)
        assert start is not None
        self.assertEqual(start.hour, 0)
        self.assertEqual(getattr(start.tzinfo, "key", str(start.tzinfo)), "Europe/Moscow")

    def test_template_formatter_bound_to_berlin(self) -> None:
        html = render_template(
            "components/datetime_cell.html",
            display_timezone="Europe/Berlin",
            iso="2025-06-15T10:00:00+00:00",
        )
        self.assertIn("12:00:00", html)
        self.assertIn("15.06.2025", html)

    def test_make_formatter_now(self) -> None:
        f = make_formatter("UTC")
        self.assertRegex(f.fmt_now(), r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")


if __name__ == "__main__":
    unittest.main()
