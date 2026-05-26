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
        self.assertIn("getsync-site", r.text)
        self.assertNotIn("Hammerhead → Garmin", r.text)

    def test_tokens_css_served(self) -> None:
        from getsync.web.app import app

        client = TestClient(app)
        r = client.get("/static/tokens.css")
        self.assertEqual(r.status_code, 200)
        self.assertIn("--getsync-primary-600", r.text)
        self.assertIn("--getsync-status-synced", r.text)

    def test_ui_preview_sidebar_layout(self) -> None:
        import tempfile
        from pathlib import Path

        from fastapi.testclient import TestClient

        from getsync.config import get_settings
        from getsync.state.store import Store
        from getsync.web.app import app
        from helpers import isolated_env

        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                store = Store(get_settings().db_path)
                store.create_user(
                    slug="preview",
                    display_name="Preview User",
                    email="preview@example.com",
                    password="secretpass123",
                    timezone="UTC",
                )
                client = TestClient(app)
                client.post(
                    "/app/login",
                    data={"email": "preview@example.com", "password": "secretpass123"},
                    follow_redirects=False,
                )
                r = client.get("/app/ui-preview")
                self.assertEqual(r.status_code, 200)
                self.assertIn("getsync-app-topbar", r.text)
                self.assertIn("UI preview", r.text)
                self.assertNotIn('type="password"', r.text)
                r2 = client.get("/app/ui-preview/settings")
                self.assertEqual(r2.status_code, 200)
                self.assertIn('id="profile"', r2.text)
                self.assertNotIn('<input ', r2.text)

    def test_app_login_uses_site_not_app_shell(self) -> None:
        from getsync.web.app import app

        client = TestClient(app)
        r = client.get("/app/login")
        self.assertEqual(r.status_code, 200)
        self.assertIn("getsync-site", r.text)
        self.assertNotIn("getsync-app-header", r.text)

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
