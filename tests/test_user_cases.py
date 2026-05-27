"""User-case flows (PLAN 2.13) — journeys from docs/design/SCREENS.md."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from getsync.state.store import Store
from getsync.web import rate_limit
from flows import (
    assert_redirect,
    assert_redirect_prefix,
    login,
    logout,
    seed_default_user,
    seed_regular_user,
)
from helpers import isolated_env


def _client_and_store(tmp: str) -> tuple[TestClient, Store]:
    from getsync.config import get_settings
    from getsync.web.app import app

    store = Store(get_settings().db_path)
    return TestClient(app), store


class TestGuestUseCases(unittest.TestCase):
    """UC-G*: guest (no session)."""

    def test_uc_g01_landing_links_to_login(self) -> None:
        """UC-G01: Guest opens landing and sees login CTA."""
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, _ = _client_and_store(tmp)
                r = client.get("/")
                self.assertEqual(r.status_code, 200)
                self.assertIn("/app/login", r.text)
                self.assertIn("getsync", r.text.lower())

    def test_uc_g02_register_closed_by_default(self) -> None:
        """UC-G02: Guest cannot register when REGISTRATION_OPEN=false."""
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="false"):
                client, _ = _client_and_store(tmp)
                r = client.get("/register")
                self.assertEqual(r.status_code, 403)

    def test_uc_g03_register_open_auto_login_to_activities(self) -> None:
        """UC-G03: Guest registers → auto-login → activities."""
        rate_limit.reset_register_limiter()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                    client, store = _client_and_store(tmp)
                    r = client.post(
                        "/register",
                        data={
                            "email": "new.rider@test.local",
                            "password": "secret123",
                            "password_confirm": "secret123",
                            "display_name": "New Rider",
                        },
                        follow_redirects=False,
                    )
                    self.assertEqual(r.status_code, 303)
                    self.assertEqual(r.headers.get("location"), "/app/activities")
                    row = store.get_user_by_email("new.rider@test.local")
                    self.assertIsNotNone(row)
                    home = client.get("/app/activities")
                    self.assertEqual(home.status_code, 200)
                    self.assertIn("new.rider@test.local", home.text)
        finally:
            rate_limit.reset_register_limiter()


class TestUserUseCases(unittest.TestCase):
    """UC-U*: authenticated user."""

    def test_uc_u01_login_journey_to_activities_and_settings(self) -> None:
        """UC-U01: Login → activities → settings (connections)."""
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store = _client_and_store(tmp)
                seed_default_user(store, "rider@test.local", "good-pass-123")
                login(client, "rider@test.local", "good-pass-123")

                activities = client.get("/app/activities")
                self.assertEqual(activities.status_code, 200)
                self.assertIn("in catalog", activities.text)
                self.assertIn("getsync-app-topbar", activities.text)

                settings = client.get("/app/settings")
                self.assertEqual(settings.status_code, 200)
                self.assertIn("connections", settings.text.lower())
                self.assertIn("section=garmin", settings.text)

                garmin = client.get("/app/settings?section=garmin")
                self.assertEqual(garmin.status_code, 200)
                self.assertIn("garmin connect", garmin.text.lower())

    def test_uc_u02_legacy_redirects(self) -> None:
        """UC-U02: /app/, /app/log, /app/session legacy URLs."""
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store = _client_and_store(tmp)
                seed_default_user(store, "rider@test.local", "good-pass-123")
                login(client, "rider@test.local", "good-pass-123")

                assert_redirect(client, "/app/", location="/app/activities")
                assert_redirect_prefix(
                    client,
                    "/app/log",
                    location_prefix="/app/admin/log",
                )
                assert_redirect_prefix(
                    client,
                    "/app/session",
                    location_prefix="/app/settings",
                )
                loc = client.get("/app/session", follow_redirects=False).headers.get(
                    "location", ""
                )
                self.assertIn("garmin-session", loc)

    def test_uc_u03_activities_calendar_view_params(self) -> None:
        """UC-U03: Calendar view accepts year/month/source query params."""
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store = _client_and_store(tmp)
                user_id = seed_default_user(store, "rider@test.local", "good-pass-123")
                store.upsert_activity(
                    user_id,
                    "hh-100",
                    name="May Ride",
                    activity_date="2026-05-15T10:00:00+00:00",
                    sync_status="synced",
                    source="hammerhead",
                )
                login(client, "rider@test.local", "good-pass-123")

                r = client.get(
                    "/app/activities",
                    params={"view": "calendar", "year": 2026, "month": 5},
                )
                self.assertEqual(r.status_code, 200)
                self.assertIn("May 2026", r.text)
                self.assertIn("view=calendar", r.text)

                r_list = client.get(
                    "/app/activities",
                    params={
                        "view": "list",
                        "date_from": "2026-05-01",
                        "date_to": "2026-05-31",
                    },
                )
                self.assertEqual(r_list.status_code, 200)
                self.assertIn('value="list"', r_list.text)
                self.assertIn("1 in catalog", r_list.text)

    def test_uc_u04_logout_requires_login_again(self) -> None:
        """UC-U04: Logout clears session."""
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store = _client_and_store(tmp)
                seed_default_user(store, "rider@test.local", "good-pass-123")
                login(client, "rider@test.local", "good-pass-123")
                logout(client)
                assert_redirect(client, "/app/activities", location="/app/login")


class TestAdminUseCases(unittest.TestCase):
    """UC-A*: admin user."""

    def test_uc_a01_admin_journey_users_and_logs(self) -> None:
        """UC-A01: Admin → users, sync log, Garmin JWT log."""
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store = _client_and_store(tmp)
                seed_default_user(store, "admin@test.local", "admin-pass-123")
                login(client, "admin@test.local", "admin-pass-123")

                users = client.get("/app/admin/")
                self.assertEqual(users.status_code, 200)
                self.assertIn("default", users.text)

                admin_log = client.get("/app/admin/log")
                self.assertEqual(admin_log.status_code, 200)
                self.assertIn("app restarts and deploys", admin_log.text)

    def test_uc_a02_non_admin_forbidden_on_admin(self) -> None:
        """UC-A02: Regular user gets 403 on /app/admin/."""
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store = _client_and_store(tmp)
                seed_default_user(store, "admin@test.local", "admin-pass-123")
                seed_regular_user(
                    store,
                    slug="user1",
                    email="user1@test.local",
                    password="user-pass-123",
                )
                login(client, "user1@test.local", "user-pass-123")
                r = client.get("/app/admin/")
                self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
