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
        self.assertIn("card shadow-sm", r.text)
        self.assertIn("Hammerhead → Garmin", r.text)
        self.assertNotIn("getsync-site", r.text)

    def test_home_page_bootstrap_sri(self) -> None:
        from getsync.web.app import app

        client = TestClient(app)
        r = client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("bootstrap@5.3.3/dist/css/bootstrap.min.css", r.text)
        # Must match jsdelivr file (wrong SRI → browser blocks all Bootstrap styles)
        self.assertIn(
            'integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH"',
            r.text,
        )

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
