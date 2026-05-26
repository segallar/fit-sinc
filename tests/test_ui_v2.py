"""Jinja templates and UI helpers (no network)."""

import unittest

from fastapi.testclient import TestClient


class TestTemplates(unittest.TestCase):
    def test_render_status_fragment(self) -> None:
        from getsync.web.templating import render_template

        html = render_template(
            "fragments/status_panel.html",
            jwt_ttl="2h",
            activity_count=3,
        )
        self.assertIn("Garmin JWT TTL", html)
        self.assertIn("2h", html)

    def test_login_page_uses_app_css(self) -> None:
        from getsync.web.app import app

        client = TestClient(app)
        r = client.get("/app/login")
        self.assertEqual(r.status_code, 200)
        self.assertIn("/static/app.css", r.text)
        self.assertIn("Sign in", r.text)

    def test_timezone_select_template(self) -> None:
        from getsync.web.templating import render_template

        html = render_template(
            "components/timezone_select.html",
            select_name="timezone",
            selected="Europe/Moscow",
        )
        self.assertIn("<select", html)
        self.assertIn("Europe/Moscow", html)
        self.assertIn("Europe/Berlin", html)
        self.assertIn("optgroup", html)


if __name__ == "__main__":
    unittest.main()
