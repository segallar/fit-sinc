"""Registration (2.1 / 2.2): REGISTRATION_OPEN, slug, validation, rate limit, auto-login."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from getsync.state.store import Store
from getsync.users.slug import allocate_unique_slug, slug_from_email
from getsync.web import rate_limit
from helpers import isolated_env

_REGISTER_FORM = {
    "email": "newuser@test.local",
    "display_name": "New User",
    "password": "secret123",
    "password_confirm": "secret123",
    "timezone": "Europe/Berlin",
}


def _post_register(client: TestClient, **overrides: str) -> object:
    data = {**_REGISTER_FORM, **overrides}
    return client.post("/register", data=data, follow_redirects=False)


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
    def setUp(self) -> None:
        rate_limit.reset_register_limiter()

    def tearDown(self) -> None:
        rate_limit.reset_register_limiter()

    def test_closed_get_returns_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="false"):
                from getsync.web.app import app

                r = TestClient(app).get("/register")
                self.assertEqual(r.status_code, 403)
                self.assertIn("недоступна", r.text)

    def test_closed_post_returns_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="false"):
                from getsync.web.app import app

                r = _post_register(TestClient(app))
                self.assertEqual(r.status_code, 403)

    def test_open_get_shows_form(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                r = TestClient(app).get("/register")
                self.assertEqual(r.status_code, 200)
                self.assertIn("Sign up", r.text)
                self.assertIn('name="email"', r.text)

    def test_register_success_auto_login_and_slug(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                client = TestClient(app)
                r = _post_register(client)
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
                self.assertEqual(user.timezone, "Europe/Berlin")
                self.assertFalse(user.is_admin)

    def test_slug_collision_allocates_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.create_user(
                    slug="roman",
                    display_name="First",
                    email="first@test.local",
                    password="password1",
                )

                from getsync.web.app import app

                client = TestClient(app)
                r = _post_register(
                    client,
                    email="roman@corp.test",
                    display_name="Second",
                )
                self.assertEqual(r.status_code, 303)
                user = store.get_user_by_email("roman@corp.test")
                assert user is not None
                self.assertEqual(user.slug, "roman-2")

    def test_empty_display_name_from_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                client = TestClient(app)
                r = _post_register(
                    client,
                    email="anna.maria@test.local",
                    display_name="",
                )
                self.assertEqual(r.status_code, 303)
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                user = Store(settings.db_path).get_user_by_email("anna.maria@test.local")
                assert user is not None
                self.assertEqual(user.display_name, "Anna Maria")

    def test_invalid_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                r = _post_register(TestClient(app), email="not-an-email")
                self.assertEqual(r.status_code, 400)
                self.assertIn("корректный email", r.text)

    def test_short_password(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                r = _post_register(
                    TestClient(app),
                    password="short",
                    password_confirm="short",
                )
                self.assertEqual(r.status_code, 400)
                self.assertIn("не короче", r.text)

    def test_password_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                r = _post_register(
                    TestClient(app),
                    password="secret123",
                    password_confirm="other123",
                )
                self.assertEqual(r.status_code, 400)
                self.assertIn("не совпадают", r.text)

    def test_duplicate_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.create_user(
                    slug="taken",
                    display_name="Taken",
                    email="taken@test.local",
                    password="password1",
                )

                from getsync.web.app import app

                r = _post_register(TestClient(app), email="taken@test.local")
                self.assertEqual(r.status_code, 400)
                self.assertIn("уже есть", r.text)

    def test_rate_limit_after_max_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                small = rate_limit._WindowLimiter(3, 60)
                with patch.object(rate_limit, "_register_limiter", small):
                    client = TestClient(app)
                    for _ in range(3):
                        r = _post_register(client, email="bad-email")
                        self.assertEqual(r.status_code, 400)
                    r = _post_register(client, email="bad-email")
                    self.assertEqual(r.status_code, 429)
                    self.assertIn("Слишком много попыток", r.text)

    def test_logged_in_user_redirects_from_register(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                client = TestClient(app)
                _post_register(client, email="member@test.local")
                r = client.get("/register", follow_redirects=False)
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers.get("location"), "/app/")

    def test_home_and_login_signup_link_when_open(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                from getsync.web.app import app

                client = TestClient(app)
                home = client.get("/")
                self.assertEqual(home.status_code, 200)
                self.assertIn("/register", home.text)
                self.assertIn("Sign up", home.text)

                login = client.get("/app/login")
                self.assertEqual(login.status_code, 200)
                self.assertIn("/register", login.text)
                self.assertIn("Sign up", login.text)

    def test_home_and_login_hide_signup_when_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="false"):
                from getsync.web.app import app

                client = TestClient(app)
                home = client.get("/")
                self.assertNotIn('href="/register"', home.text)

                login = client.get("/app/login")
                self.assertNotIn('href="/register"', login.text)


if __name__ == "__main__":
    unittest.main()
