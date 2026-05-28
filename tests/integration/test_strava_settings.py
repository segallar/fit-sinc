"""Strava OAuth settings flow (**3.9.3c** Phase 1)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from getsync.providers.strava.oauth import TokenSet
from getsync.web.oauth_state import sign_strava_oauth_state, verify_strava_oauth_state
from helpers import isolated_env


class TestStravaOAuthState(unittest.TestCase):
    def test_sign_verify_roundtrip(self) -> None:
        state = sign_strava_oauth_state("user-1", "secret")
        self.assertEqual(verify_strava_oauth_state(state, "secret"), "user-1")
        self.assertIsNone(verify_strava_oauth_state(state, "wrong"))


class TestStravaSettings(unittest.TestCase):
    def test_settings_strava_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(
                Path(tmp),
                STRAVA_CLIENT_ID="252416",
                STRAVA_CLIENT_SECRET="test-secret",
            ):
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
                page = client.get("/app/settings?section=strava")
                self.assertEqual(page.status_code, 200)
                self.assertIn("Strava", page.text)
                self.assertIn("/app/settings/strava/connect", page.text)
                self.assertIn("Source + Destination", page.text)

    @patch("getsync.web.settings_routes.StravaOAuth.exchange_code", new_callable=AsyncMock)
    def test_strava_callback_saves_tokens(self, mock_exchange: AsyncMock) -> None:
        mock_exchange.return_value = TokenSet(
            access_token="at",
            refresh_token="rt",
            expires_at=9_999_999_999.0,
            athlete_id=42,
            obtained_at=1.0,
        )
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(
                Path(tmp),
                STRAVA_CLIENT_ID="252416",
                STRAVA_CLIENT_SECRET="test-secret",
            ):
                from getsync.config import get_settings
                from getsync.providers.strava.client import StravaClient
                from getsync.state.store import Store
                from getsync.users.context import UserContext
                from getsync.web.app import app

                settings = get_settings()
                store = Store(settings.db_path)
                user = store.ensure_default_user(
                    email="owner@test.local",
                    password="good-pass",
                )
                client = TestClient(app)
                client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "good-pass"},
                    follow_redirects=False,
                )
                state = sign_strava_oauth_state(user.id, settings.session_secret)
                r = client.get(
                    f"/app/settings/strava/callback?code=abc&state={state}",
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertIn("section=strava", r.headers.get("location", ""))
                self.assertIn("msg=strava_connected", r.headers.get("location", ""))
                ctx = UserContext(user.id, settings)
                tokens = StravaClient(ctx).load_tokens()
                self.assertIsNotNone(tokens)
                assert tokens is not None
                self.assertEqual(tokens.athlete_id, 42)
