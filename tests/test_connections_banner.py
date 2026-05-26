"""Dashboard connections banner (1.8)."""

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from helpers import isolated_env


class TestConnectionsBanner(unittest.TestCase):
    def test_settings_shows_connections_section(self) -> None:
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

                settings_page = client.get("/app/settings", follow_redirects=True)
                self.assertEqual(settings_page.status_code, 200)
                self.assertIn("Hammerhead", settings_page.text)
                self.assertIn("Garmin Connect", settings_page.text)

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
