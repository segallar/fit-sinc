"""Registration (2.1): REGISTRATION_OPEN, slug, auto-login."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from getsync.state.store import Store
from getsync.users.slug import allocate_unique_slug, slug_from_email
from helpers import isolated_env


class TestSlugFromEmail(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(slug_from_email("Roman@Example.com"), "roman")

    def test_dots_and_plus(self) -> None:
        self.assertEqual(slug_from_email("a.b+c@x.co"), "a_b_c")

    def test_allocate_unique(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.create_user(
                    slug="roman",
                    display_name="R",
                    email="one@test.local",
                    password="password1",
                )
                self.assertEqual(allocate_unique_slug(store, "roman"), "roman-2")


class TestRegisterRoutes(unittest.TestCase):
    def test_closed_returns_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="false"):
                from getsync.web.app import app

                client = TestClient(app)
                r = client.get("/register")
                self.assertEqual(r.status_code, 403)
                self.assertIn("закрыта", r.text)

    def test_register_and_login_redirects_to_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                client = TestClient(app)
                r = client.post(
                    "/register",
                    data={
                        "email": "newuser@test.local",
                        "display_name": "New User",
                        "password": "secret123",
                        "password_confirm": "secret123",
                        "timezone": "Europe/Berlin",
                    },
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers.get("location"), "/app/")

                dash = client.get("/app/", follow_redirects=False)
                self.assertEqual(dash.status_code, 200)
                self.assertIn("newuser@test.local", dash.text)

                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                user = store.get_user_by_email("newuser@test.local")
                assert user is not None
                self.assertEqual(user.slug, "newuser")
                self.assertFalse(user.is_admin)

    def test_home_has_login_and_signup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                client = TestClient(app)
                r = client.get("/")
                self.assertEqual(r.status_code, 200)
                self.assertIn("/app/login", r.text)
                self.assertIn("/register", r.text)
                self.assertIn("Sign up", r.text)


if __name__ == "__main__":
    unittest.main()
