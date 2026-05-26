"""Settings page and profile update (no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from getsync.state.store import Store
from helpers import isolated_env


class TestSettings(unittest.TestCase):
    def test_settings_requires_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                client = TestClient(app)
                r = client.get("/app/settings", follow_redirects=False)
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers.get("location"), "/app/login")

    def test_settings_profile_and_nav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.ensure_default_user(
                    email="owner@test.local",
                    password="good-pass",
                )

                from getsync.web.app import app

                client = TestClient(app)
                client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "good-pass"},
                    follow_redirects=False,
                )
                page = client.get("/app/settings")
                self.assertEqual(page.status_code, 200)
                self.assertIn("Settings", page.text)
                self.assertIn("/app/settings", page.text)

                home = client.get("/app/", follow_redirects=True)
                self.assertIn("Activities", home.text)

                r = client.post(
                    "/app/settings/profile",
                    data={
                        "display_name": "Roman",
                        "email": "owner@test.local",
                        "telegram": "@roman",
                        "timezone": "Europe/Berlin",
                    },
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertIn("msg=profile_saved", r.headers.get("location", ""))

                user = store.get_user("default")
                assert user is not None
                self.assertEqual(user.display_name, "Roman")
                self.assertEqual(user.timezone, "Europe/Berlin")


if __name__ == "__main__":
    unittest.main()
