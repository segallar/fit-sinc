"""App and admin session login (no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from fit_sinc.state.store import Store
from helpers import isolated_env


class TestAppLogin(unittest.TestCase):
    def test_login_success_and_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "fit_sinc.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.ensure_default_user(
                    email="owner@test.local",
                    password="good-pass",
                )

                from fit_sinc.web.app import app

                client = TestClient(app)
                r = client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "good-pass"},
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers.get("location"), "/app/")

                dash = client.get("/app/", follow_redirects=False)
                self.assertEqual(dash.status_code, 200)
                self.assertIn("Connections", dash.text)

    def test_login_wrong_password_redirects_with_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "fit_sinc.config", fromlist=["get_settings"]
                ).get_settings()
                Store(settings.db_path).ensure_default_user(
                    email="owner@test.local",
                    password="good-pass",
                )

                from fit_sinc.web.app import app

                client = TestClient(app)
                r = client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "wrong"},
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertIn("error=1", r.headers.get("location", ""))

    def test_app_requires_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from fit_sinc.web.app import app

                client = TestClient(app)
                r = client.get("/app/activities", follow_redirects=False)
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers.get("location"), "/app/login")


class TestAdminLogin(unittest.TestCase):
    def test_admin_login_and_users_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "fit_sinc.config", fromlist=["get_settings"]
                ).get_settings()
                Store(settings.db_path).ensure_default_user(password="x")

                from fit_sinc.web.app import app

                client = TestClient(app)
                r = client.post(
                    "/admin/login",
                    data={
                        "username": settings.admin_username,
                        "password": "admin-test-pass",
                    },
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers.get("location"), "/admin/")

                users = client.get("/admin/")
                self.assertEqual(users.status_code, 200)
                self.assertIn("default", users.text)


if __name__ == "__main__":
    unittest.main()
