"""Session auth security regression tests (no network)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from fit_sinc.config import get_settings
from fit_sinc.state.store import Store
from helpers import isolated_env, webhook_hmac

LOGIN_REDIRECT = "/app/login"

APP_GET_PATHS = (
    "/app/",
    "/app/activities",
    "/app/log",
    "/app/session",
    "/app/settings",
)

ADMIN_GET_PATHS = (
    "/app/admin/",
    "/app/admin/users/new",
    "/app/admin/users/default/edit",
)

APP_POST_CASES: tuple[tuple[str, dict[str, str]], ...] = (
    ("/app/session/refresh", {}),
    ("/app/activities/act-1/retry", {"next": "/app/activities"}),
    ("/app/activities/retry-errors", {"next": "/app/activities"}),
)

ADMIN_POST_CASES: tuple[tuple[str, dict[str, str]], ...] = (
    (
        "/app/admin/users/new",
        {
            "slug": "newbie",
            "display_name": "New",
            "email": "new@test.local",
            "password": "long-enough",
            "timezone": "Europe/Moscow",
        },
    ),
    (
        "/app/admin/users/default/edit",
        {
            "display_name": "Default",
            "email": "owner@local",
            "timezone": "Europe/Moscow",
        },
    ),
)


def _settings():
    return get_settings()


def _login(client: TestClient, email: str, password: str) -> None:
    r = client.post(
        "/app/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )
    assert r.status_code == 303, r.text


def _assert_login_redirect(test: unittest.TestCase, response) -> None:
    test.assertEqual(response.status_code, 303)
    test.assertEqual(response.headers.get("location"), LOGIN_REDIRECT)


def _make_client(
    tmp: str,
    *,
    admin_email: str = "admin@test.local",
    admin_password: str = "admin-pass",
) -> tuple[TestClient, Store, str]:
    settings = _settings()
    store = Store(settings.db_path)
    store.ensure_default_user(email=admin_email, password=admin_password)
    from fit_sinc.web.app import app

    return TestClient(app), store, settings.default_user_id


class TestPublicRoutes(unittest.TestCase):
    def test_public_routes_without_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, _, _ = _make_client(tmp)
                for path, status in (
                    ("/", 200),
                    ("/health", 200),
                    ("/app/login", 200),
                ):
                    with self.subTest(path=path):
                        r = client.get(path, follow_redirects=False)
                        self.assertEqual(r.status_code, status)

                css = client.get("/static/app.css", follow_redirects=False)
                self.assertIn(css.status_code, (200, 304))


class TestAppRoutesRequireSession(unittest.TestCase):
    def test_app_get_pages_redirect_without_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, _, _ = _make_client(tmp)
                for path in APP_GET_PATHS:
                    with self.subTest(path=path):
                        _assert_login_redirect(self, client.get(path, follow_redirects=False))

    def test_app_post_redirects_without_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, _, _ = _make_client(tmp)
                for path, data in APP_POST_CASES:
                    with self.subTest(path=path):
                        _assert_login_redirect(
                            self,
                            client.post(path, data=data, follow_redirects=False),
                        )

    def test_fit_download_redirects_without_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, _, _ = _make_client(tmp)
                _assert_login_redirect(
                    self,
                    client.get("/app/activities/secret-act/fit", follow_redirects=False),
                )

    @patch("fit_sinc.web.app_routes._run_sync_force", new_callable=AsyncMock)
    @patch("fit_sinc.web.app_routes.refresh_web_session")
    def test_app_post_allowed_with_session(
        self,
        _mock_refresh,
        _mock_sync: AsyncMock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store, user_id = _make_client(tmp)
                store.upsert_activity(user_id, "act-1", sync_status="error")
                _login(client, "admin@test.local", "admin-pass")

                for path, data in APP_POST_CASES:
                    with self.subTest(path=path):
                        r = client.post(path, data=data, follow_redirects=False)
                        self.assertEqual(r.status_code, 303, path)
                        self.assertNotEqual(r.headers.get("location"), LOGIN_REDIRECT)


class TestAdminRoutesRequireSession(unittest.TestCase):
    def test_admin_get_redirects_without_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, _, _ = _make_client(tmp)
                for path in ADMIN_GET_PATHS:
                    with self.subTest(path=path):
                        _assert_login_redirect(self, client.get(path, follow_redirects=False))

    def test_admin_post_redirects_without_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, _, _ = _make_client(tmp)
                for path, data in ADMIN_POST_CASES:
                    with self.subTest(path=path):
                        _assert_login_redirect(
                            self,
                            client.post(path, data=data, follow_redirects=False),
                        )

    def test_non_admin_gets_403_on_admin_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store, _ = _make_client(tmp)
                store.create_user(
                    slug="user1",
                    display_name="User",
                    email="u@test.local",
                    password="secret",
                    user_id="user1",
                    is_admin=False,
                )
                _login(client, "u@test.local", "secret")

                for path in ADMIN_GET_PATHS:
                    with self.subTest(path=path):
                        r = client.get(path, follow_redirects=False)
                        self.assertEqual(r.status_code, 403, path)

                for path, data in ADMIN_POST_CASES:
                    with self.subTest(path=path):
                        r = client.post(path, data=data, follow_redirects=False)
                        self.assertEqual(r.status_code, 403, path)


class TestInvalidSession(unittest.TestCase):
    def test_deleted_user_session_treated_as_anonymous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store, _ = _make_client(tmp)
                store.create_user(
                    slug="ghost",
                    display_name="Ghost",
                    email="ghost@test.local",
                    password="secret",
                    user_id="ghost",
                )
                _login(client, "ghost@test.local", "secret")
                with store._conn() as conn:
                    conn.execute("DELETE FROM users WHERE id = ?", ("ghost",))

                _assert_login_redirect(self, client.get("/app/", follow_redirects=False))

    def test_disabled_user_cannot_login(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store, _ = _make_client(tmp)
                store.create_user(
                    slug="blocked",
                    display_name="Blocked",
                    email="blocked@test.local",
                    password="secret",
                    user_id="blocked",
                )
                store.update_user("blocked", disabled=True)
                r = client.post(
                    "/app/login",
                    data={"email": "blocked@test.local", "password": "secret"},
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertIn("error=1", r.headers.get("location", ""))

    def test_disabled_user_session_treated_as_anonymous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store, _ = _make_client(tmp)
                store.create_user(
                    slug="blocked",
                    display_name="Blocked",
                    email="live@test.local",
                    password="secret",
                    user_id="blocked",
                )
                _login(client, "live@test.local", "secret")
                store.update_user("blocked", disabled=True)
                _assert_login_redirect(self, client.get("/app/", follow_redirects=False))


class TestTenantIsolation(unittest.TestCase):
    def test_user_cannot_download_other_users_fit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store, _ = _make_client(tmp)
                store.create_user(
                    slug="alice",
                    display_name="Alice",
                    email="alice@test.local",
                    password="alice-pass",
                    user_id="alice",
                )
                store.create_user(
                    slug="bob",
                    display_name="Bob",
                    email="bob@test.local",
                    password="bob-pass",
                    user_id="bob",
                )
                bob_ctx = __import__(
                    "fit_sinc.users.context", fromlist=["resolve_user_context"]
                ).resolve_user_context("bob")
                bob_ctx.fits_dir.mkdir(parents=True, exist_ok=True)
                fit_path = bob_ctx.fits_dir / "bob-act.fit"
                fit_path.write_bytes(b"FIT")
                store.upsert_activity(
                    "bob",
                    "bob-act",
                    name="Bob ride",
                    sync_status="synced",
                    fit_path=str(fit_path),
                )

                _login(client, "alice@test.local", "alice-pass")
                r = client.get("/app/activities/bob-act/fit", follow_redirects=False)
                self.assertEqual(r.status_code, 404)

    def test_dashboard_shows_only_own_activities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                client, store, _ = _make_client(tmp)
                store.create_user(
                    slug="alice",
                    display_name="Alice",
                    email="alice@test.local",
                    password="alice-pass",
                    user_id="alice",
                )
                store.upsert_activity("alice", "alice-act", name="Alice ride")
                store.upsert_activity("default", "admin-act", name="Admin secret ride")

                _login(client, "alice@test.local", "alice-pass")
                r = client.get("/app/", follow_redirects=False)
                self.assertEqual(r.status_code, 200)
                self.assertIn("Alice ride", r.text)
                self.assertNotIn("Admin secret ride", r.text)


class TestWebhookSecurity(unittest.TestCase):
    def test_rejects_missing_hmac_when_secret_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from fit_sinc.web.app import app

                client = TestClient(app)
                body = b'{"activityId":"a1"}'
                r = client.post("/webhooks/hammerhead", content=body)
                self.assertEqual(r.status_code, 403)
                self.assertEqual(r.json()["status"], "forbidden")

    def test_rejects_invalid_hmac(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from fit_sinc.web.app import app

                client = TestClient(app)
                body = b'{"activityId":"a1"}'
                r = client.post(
                    "/webhooks/hammerhead",
                    content=body,
                    headers={"X-Hmac-Signature": "deadbeef"},
                )
                self.assertEqual(r.status_code, 403)

    @patch("fit_sinc.web.app.sync_activity", new_callable=AsyncMock)
    def test_accepts_valid_hmac_without_session(self, _mock_sync: AsyncMock) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from fit_sinc.web.app import app

                client = TestClient(app)
                payload = {"activityId": "a1", "userId": "1"}
                body = json.dumps(payload).encode()
                r = client.post(
                    "/webhooks/hammerhead",
                    content=body,
                    headers={"X-Hmac-Signature": webhook_hmac(body, "test-webhook-secret")},
                )
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json()["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
