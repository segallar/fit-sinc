"""Dashboard connections banner (1.8)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from helpers import isolated_env


class TestConnectionsBanner(unittest.TestCase):
    def test_settings_connection_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.config import get_settings
                from getsync.state.store import Store
                from getsync.web.app import app

                store = Store(get_settings().db_path)
                store.ensure_default_user(
                    email="owner@test.local",
                    password="good-pass",
                )

                client = TestClient(app)
                r = client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "good-pass"},
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)

                settings_page = client.get(
                    "/app/settings?section=garmin",
                    follow_redirects=True,
                )
                self.assertEqual(settings_page.status_code, 200)
                self.assertIn("Garmin Connect", settings_page.text)
                self.assertIn("Garmin web session", settings_page.text)
                self.assertIn('name="garmin_email"', settings_page.text)
                self.assertIn('name="garmin_password"', settings_page.text)
                self.assertNotIn("getsync --user", settings_page.text)

                hh_page = client.get("/app/settings?section=hammerhead")
                self.assertEqual(hh_page.status_code, 200)
                self.assertIn("Hammerhead", hh_page.text)
                self.assertNotIn("Garmin web session", hh_page.text)

    @patch("getsync.web.settings_routes.garmin_login")
    def test_garmin_login_from_settings(self, mock_login) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.config import get_settings
                from getsync.state.store import Store
                from getsync.web.app import app

                store = Store(get_settings().db_path)
                store.ensure_default_user(
                    email="owner@test.local",
                    password="good-pass",
                )
                client = TestClient(app)
                client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "good-pass"},
                    follow_redirects=False,
                )
                r = client.post(
                    "/app/settings/garmin/login",
                    data={
                        "garmin_email": "runner@garmin.com",
                        "garmin_password": "secret",
                        "save_credentials": "on",
                    },
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                loc = r.headers.get("location", "")
                self.assertIn("section=garmin", loc)
                self.assertIn("msg=garmin_connected", loc)
                mock_login.assert_called_once()
                args, kwargs = mock_login.call_args
                self.assertEqual(args[0], "runner@garmin.com")
                self.assertEqual(args[1], "secret")
                self.assertTrue(kwargs.get("save_credentials"))
                self.assertTrue(kwargs.get("store_password"))

    def test_garmin_login_requires_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.config import get_settings
                from getsync.state.store import Store
                from getsync.web.app import app

                Store(get_settings().db_path).ensure_default_user(
                    email="owner@test.local",
                    password="good-pass",
                )
                client = TestClient(app)
                client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "good-pass"},
                    follow_redirects=False,
                )
                r = client.post(
                    "/app/settings/garmin/login",
                    data={"garmin_email": "", "garmin_password": ""},
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertIn("error=garmin_credentials_required", r.headers.get("location", ""))

    def test_connection_status_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.config import get_settings
                from getsync.state.store import Store
                from getsync.users.context import resolve_user_context
                from getsync.web.connections import connection_status

                store = Store(get_settings().db_path)
                user = store.ensure_default_user(
                    email="u@test.local",
                    password="pass",
                )
                ctx = resolve_user_context(user.id)
                status = connection_status(ctx, user)
                self.assertIn("hammerhead", status)
                self.assertIn("garmin", status)
                self.assertIn("upload_ready", status["garmin"])
                self.assertIn("ttl_sec", status["garmin"])


if __name__ == "__main__":
    unittest.main()
