"""Smoke tests for CI (stdlib unittest, no network)."""

import unittest

from fit_sinc.hammerhead.oauth import TokenSet, verify_webhook_signature


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
        from fit_sinc.web.app import app

        self.assertEqual(app.title, "fit_sinc")

    def test_token_set_roundtrip(self) -> None:
        ts = TokenSet("a", "r", 3600, "u1", 1000.0)
        restored = TokenSet.from_dict(ts.to_dict())
        self.assertEqual(restored.access_token, "a")
        self.assertEqual(restored.user_id, "u1")


class TestStore(unittest.TestCase):
    def test_sqlite_init(self) -> None:
        import tempfile
        from pathlib import Path

        from fit_sinc.state.store import Store

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "test.db"
            store = Store(db)
            self.assertFalse(store.is_synced("nonexistent-id"))


if __name__ == "__main__":
    unittest.main()
