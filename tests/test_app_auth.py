"""App and admin session login (no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from getsync.state.store import Store
from helpers import isolated_env


class TestAppLogin(unittest.TestCase):
    def test_login_success_and_dashboard(self) -> None:
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
                r = client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "good-pass"},
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers.get("location"), "/app/activities")

                home = client.get("/app/", follow_redirects=False)
                self.assertEqual(home.status_code, 303)
                self.assertEqual(home.headers.get("location"), "/app/activities")

                dash = client.get("/app/activities", follow_redirects=False)
                self.assertEqual(dash.status_code, 200)
                self.assertIn("Sync log", dash.text)
                self.assertIn("getsync-app-topbar", dash.text)
                self.assertIn("owner@test.local", dash.text)
                self.assertIn("/app/logout", dash.text)
                self.assertNotIn('nav><a href="/app/logout">Logout</a>', dash.text)

    def test_session_cookie_secure_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(
                Path(tmp),
                SESSION_COOKIE_SECURE="true",
            ):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                self.assertTrue(settings.session_cookie_secure)

    def test_legacy_fit_sinc_session_cookie(self) -> None:
        import json
        from base64 import b64encode

        import itsdangerous

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

                signer = itsdangerous.TimestampSigner(settings.session_secret)
                payload = b64encode(
                    json.dumps({"user_id": "default"}).encode("utf-8")
                )
                legacy = signer.sign(payload).decode("utf-8")

                from getsync.web.app import app

                client = TestClient(app)
                client.cookies.set("fit_sinc_session", legacy)
                dash = client.get("/app/activities", follow_redirects=False)
                self.assertEqual(dash.status_code, 200)
                self.assertIn("owner@test.local", dash.text)

    def test_login_wrong_password_redirects_with_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                Store(settings.db_path).ensure_default_user(
                    email="owner@test.local",
                    password="good-pass",
                )

                from getsync.web.app import app

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
                from getsync.web.app import app

                client = TestClient(app)
                r = client.get("/app/activities", follow_redirects=False)
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers.get("location"), "/app/login")


class TestAdminAccess(unittest.TestCase):
    def test_admin_user_reaches_app_admin_users(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                Store(settings.db_path).ensure_default_user(
                    email="admin@test.local",
                    password="admin-pass",
                )

                from getsync.web.app import app

                client = TestClient(app)
                r = client.post(
                    "/app/login",
                    data={"email": "admin@test.local", "password": "admin-pass"},
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)

                users = client.get("/app/admin/")
                self.assertEqual(users.status_code, 200)
                self.assertIn("default", users.text)
                self.assertIn("getsync-app-topbar", users.text)
                self.assertIn("admin@test.local", users.text)

                log_page = client.get("/app/admin/log")
                self.assertEqual(log_page.status_code, 200)
                self.assertIn("Garmin JWT refresh log", log_page.text)

                settings = client.get("/app/settings")
                self.assertEqual(settings.status_code, 200)
                self.assertNotIn("Refresh log", settings.text)

                new_user = client.get("/app/admin/users/new")
                self.assertEqual(new_user.status_code, 200)
                self.assertIn('class="card shadow-sm"', new_user.text)
                self.assertIn('action="/app/admin/users/new"', new_user.text)

    def test_non_admin_forbidden_on_app_admin(self) -> None:
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
                store.create_user(
                    slug="user1",
                    display_name="User",
                    email="u@test.local",
                    password="secret",
                    user_id="user1",
                    is_admin=False,
                )

                from getsync.web.app import app

                client = TestClient(app)
                client.post(
                    "/app/login",
                    data={"email": "u@test.local", "password": "secret"},
                    follow_redirects=False,
                )
                r = client.get("/app/admin/")
                self.assertEqual(r.status_code, 403)

    def test_legacy_admin_redirects_to_app_admin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                Store(settings.db_path).ensure_default_user(
                    email="owner@test.local",
                    password="admin-pass",
                )

                from getsync.web.app import app

                client = TestClient(app)
                client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "admin-pass"},
                    follow_redirects=False,
                )
                r = client.get("/admin/", follow_redirects=False)
                self.assertEqual(r.status_code, 301)
                self.assertEqual(r.headers.get("location"), "/app/admin/")


class TestAppLoginI18n(unittest.TestCase):
    def test_login_default_english(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                r = TestClient(app).get("/app/login")
                self.assertEqual(r.status_code, 200)
                self.assertIn("Sign in", r.text)
                self.assertIn('lang="en"', r.text)
                self.assertIn('id="siteLangDropdown"', r.text)

    def test_login_russian_via_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app
                from getsync.web.site_i18n import LANG_COOKIE

                client = TestClient(app)
                client.cookies.set(LANG_COOKIE, "ru")
                r = client.get("/app/login")
                self.assertIn("Войти", r.text)
                self.assertIn('lang="ru"', r.text)
                self.assertIn("Преимущества", r.text)
                self.assertIn("getsync-site-footer", r.text)

    def test_login_german_via_query_sets_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app
                from getsync.web.site_i18n import LANG_COOKIE

                r = TestClient(app).get("/app/login?lang=de", follow_redirects=False)
                self.assertEqual(r.status_code, 200)
                self.assertIn("Anmelden", r.text)
                self.assertEqual(r.cookies.get(LANG_COOKIE), "de")
                self.assertIn("/set-lang?lang=de&next=", r.text)

    def test_login_lang_switcher_uses_set_lang(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                r = TestClient(app).get("/app/login")
                self.assertIn("/set-lang?lang=ru&next=%2Fapp%2Flogin", r.text)
                self.assertIn("getsync-site", r.text)
                self.assertIn('id="siteNav"', r.text)


if __name__ == "__main__":
    unittest.main()
