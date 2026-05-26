"""Timezone list and validation."""

import unittest

from getsync.users.timezones import (
    DEFAULT_TIMEZONE,
    normalize_timezone,
    options_for_select,
    timezone_choices,
)
from getsync.web.templating import render_template


class TestTimezones(unittest.TestCase):
    def test_default_timezone_valid(self) -> None:
        self.assertEqual(normalize_timezone(""), DEFAULT_TIMEZONE)
        self.assertEqual(normalize_timezone("Europe/Berlin"), "Europe/Berlin")

    def test_invalid_timezone_raises(self) -> None:
        with self.assertRaises(ValueError):
            normalize_timezone("Not/A/Zone")

    def test_choices_include_moscow(self) -> None:
        self.assertIn("Europe/Moscow", timezone_choices())

    def test_select_html_renders(self) -> None:
        field = render_template(
            "components/timezone_select.html",
            select_name="timezone",
            selected="Europe/Moscow",
        )
        self.assertIn("<select", field)
        self.assertIn("Europe/Moscow", field)
        self.assertIn("Europe/Berlin", field)
        self.assertIn("optgroup", field)

    def test_legacy_value_in_options(self) -> None:
        opts = [v for _g, v, _s in options_for_select("Europe/Berlin")]
        self.assertIn("Europe/Berlin", opts)


if __name__ == "__main__":
    unittest.main()
