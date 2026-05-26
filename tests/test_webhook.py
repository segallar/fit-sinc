"""Webhook HMAC endpoint and tenant routing (no network)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from getsync.state.store import Store
from getsync.sync.service import SyncResult, resolve_user_for_webhook
from helpers import isolated_env, webhook_hmac


class TestResolveUserForWebhook(unittest.TestCase):
    def test_maps_hammerhead_user_id_to_tenant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with isolated_env(root):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.ensure_default_user(password="x")
                store.create_user(
                    slug="roman",
                    display_name="Roman",
                    email="r@test.local",
                    password="secret",
                    hammerhead_user_id="hh-999",
                    user_id="roman",
                )
                ctx = resolve_user_for_webhook("hh-999")
                self.assertEqual(ctx.user_id, "roman")

    def test_unknown_hammerhead_user_falls_back_to_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                Store(settings.db_path).ensure_default_user(password="x")
                ctx = resolve_user_for_webhook("no-such-hh-user")
                self.assertEqual(ctx.user_id, settings.default_user_id)


class TestWebhookEndpoint(unittest.TestCase):
    def test_rejects_invalid_hmac(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                client = TestClient(app)
                body = b'{"activityId":"a1"}'
                r = client.post(
                    "/webhooks/hammerhead",
                    content=body,
                    headers={"X-Hmac-Signature": "deadbeef"},
                )
                self.assertEqual(r.status_code, 403)
                self.assertEqual(r.json()["status"], "forbidden")

    def test_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                client = TestClient(app)
                body = b"not-json"
                secret = "test-webhook-secret"
                r = client.post(
                    "/webhooks/hammerhead",
                    content=body,
                    headers={"X-Hmac-Signature": webhook_hmac(body, secret)},
                )
                self.assertEqual(r.status_code, 400)

    def test_accepts_valid_hmac_without_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                client = TestClient(app)
                body = b'{"userId":"1"}'
                secret = "test-webhook-secret"
                r = client.post(
                    "/webhooks/hammerhead",
                    content=body,
                    headers={"X-Hmac-Signature": webhook_hmac(body, secret)},
                )
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r.json()["status"], "accepted")

    def test_routes_activity_to_tenant_and_logs_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.ensure_default_user(password="x")
                store.create_user(
                    slug="rider",
                    display_name="Rider",
                    email="rider@test.local",
                    password="p",
                    hammerhead_user_id="hh-42",
                    user_id="rider",
                )

                mock_sync = AsyncMock(
                    return_value=SyncResult("act-99", "skipped", "test")
                )
                with patch("getsync.web.app.sync_activity", mock_sync):
                    from getsync.web.app import app

                    client = TestClient(app)
                    payload = {"activityId": "act-99", "userId": "hh-42"}
                    body = json.dumps(payload).encode()
                    secret = "test-webhook-secret"
                    r = client.post(
                        "/webhooks/hammerhead",
                        content=body,
                        headers={"X-Hmac-Signature": webhook_hmac(body, secret)},
                    )

                self.assertEqual(r.status_code, 200)
                mock_sync.assert_awaited_once()
                self.assertEqual(mock_sync.await_args.kwargs["user_id"], "rider")

                events = store.list_events(user_id="rider", limit=5)
                self.assertTrue(
                    any(e.event_type == "webhook_received" for e in events)
                )


if __name__ == "__main__":
    unittest.main()
