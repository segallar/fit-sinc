"""CredentialStore and Garmin credentials (2.16)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet
from getsync.credentials.garmin import (
    clear_garmin_credentials,
    garmin_auto_login_configured,
    load_garmin_login,
    save_garmin_login,
)
from getsync.credentials.store import CredentialStore, CredentialStoreError
from getsync.users.context import resolve_user_context
from helpers import isolated_env


class TestCredentialStore(unittest.TestCase):
    def test_encrypt_roundtrip(self) -> None:
        key = Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), GETSYNC_SECRETS_KEY=key):
                ctx = resolve_user_context("default")
                store = CredentialStore(ctx)
                store.save_secrets("garmin", {"password": "secret-pass"})
                data = store.load_secrets("garmin")
                self.assertEqual(data["password"], "secret-pass")
                meta = {"email": "u@example.com", "store_password_for_auto_login": True}
                store.save_meta("garmin", meta)
                self.assertEqual(store.load_meta("garmin")["email"], "u@example.com")

    def test_missing_key_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), GETSYNC_SECRETS_KEY=""):
                ctx = resolve_user_context("default")
                store = CredentialStore(ctx)
                with self.assertRaises(CredentialStoreError):
                    store.save_secrets("garmin", {"password": "x"})


class TestGarminCredentials(unittest.TestCase):
    def test_save_and_load_login(self) -> None:
        key = Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), GETSYNC_SECRETS_KEY=key):
                ctx = resolve_user_context("default")
                save_garmin_login(ctx, "runner@example.com", "pw", store_password=True)
                self.assertTrue(garmin_auto_login_configured(ctx))
                loaded = load_garmin_login(ctx)
                self.assertIsNotNone(loaded)
                assert loaded is not None
                self.assertEqual(loaded[0], "runner@example.com")
                self.assertEqual(loaded[1], "pw")

    def test_no_password_when_not_stored(self) -> None:
        key = Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), GETSYNC_SECRETS_KEY=key):
                ctx = resolve_user_context("default")
                save_garmin_login(ctx, "runner@example.com", "pw", store_password=False)
                self.assertFalse(garmin_auto_login_configured(ctx))
                self.assertIsNone(load_garmin_login(ctx))

    def test_clear(self) -> None:
        key = Fernet.generate_key().decode()
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), GETSYNC_SECRETS_KEY=key):
                ctx = resolve_user_context("default")
                save_garmin_login(ctx, "a@b.c", "pw", store_password=True)
                clear_garmin_credentials(ctx)
                self.assertIsNone(load_garmin_login(ctx))
