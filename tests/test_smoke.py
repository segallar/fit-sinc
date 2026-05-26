"""Smoke tests for CI (stdlib unittest, no network)."""

import unittest

from getsync.hammerhead.oauth import TokenSet, verify_webhook_signature


class TestWebhookHmac(unittest.TestCase):
    def test_valid_hex_signature(self) -> None:
        body = b'{"activityId":"a","userId":"1"}'
        secret = "test-secret"
        import hashlib
        import hmac

        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        self.assertTrue(verify_webhook_signature(body, secret, digest))

    def test_rejects_missing_secret(self) -> None:
        self.assertFalse(verify_webhook_signature(b"{}", "", "abc"))

    def test_rejects_wrong_signature(self) -> None:
        self.assertFalse(verify_webhook_signature(b"{}", "secret", "deadbeef"))


class TestImports(unittest.TestCase):
    def test_fastapi_app(self) -> None:
        from getsync.web.app import app

        self.assertEqual(app.title, "GetSync")

    def test_root_landing_not_500(self) -> None:
        from fastapi.testclient import TestClient

        from getsync.web.app import app

        client = TestClient(app, raise_server_exceptions=True)
        r = client.get("/", follow_redirects=False)
        self.assertEqual(r.status_code, 200)
        self.assertIn("GetSync", r.text)
        self.assertIn("/app/login", r.text)
        self.assertNotIn("fit_sinc", r.text.lower())
        self.assertNotIn("fit.romansegalla", r.text.lower())

    def test_root_redirects_when_logged_in(self) -> None:
        import tempfile
        from pathlib import Path

        from fastapi.testclient import TestClient

        from getsync.state.store import Store
        from helpers import isolated_env

        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                Store(settings.db_path).ensure_default_user(
                    email="u@test.local",
                    password="secret",
                )
                from getsync.web.app import app

                client = TestClient(app)
                client.post(
                    "/app/login",
                    data={"email": "u@test.local", "password": "secret"},
                    follow_redirects=False,
                )
                r = client.get("/", follow_redirects=False)
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.headers.get("location"), "/app/activities")

    def test_token_set_roundtrip(self) -> None:
        ts = TokenSet("a", "r", 3600, "u1", 1000.0)
        restored = TokenSet.from_dict(ts.to_dict())
        self.assertEqual(restored.access_token, "a")
        self.assertEqual(restored.user_id, "u1")


class TestStore(unittest.TestCase):
    def test_sqlite_init(self) -> None:
        import tempfile
        from pathlib import Path

        from getsync.state.store import Store
        from getsync.users.context import DEFAULT_USER_ID

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            store = Store(db)
            store.ensure_default_user(password="test")
            self.assertFalse(store.is_synced(DEFAULT_USER_ID, "nonexistent-id"))
            user = store.get_user(DEFAULT_USER_ID)
            self.assertIsNotNone(user)


if __name__ == "__main__":
    unittest.main()
