"""Phase 5b.0: admin bootstrap and registration policy (no network)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from getsync.state.store import Store
from getsync.users.bootstrap import apply_bootstrap_admin, registration_is_open
from helpers import isolated_env


class TestBootstrapAdmin(unittest.TestCase):
    def test_promotes_default_when_no_admins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.ensure_default_user(email="owner@test.local", password="x")
                store.set_admin("default", is_admin=False)

                apply_bootstrap_admin(store, settings)

                user = store.get_user("default")
                assert user is not None
                self.assertTrue(user.is_admin)

    def test_bootstrap_admin_email(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(
                Path(tmp),
                BOOTSTRAP_ADMIN_EMAIL="ops@test.local",
            ):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.create_user(
                    slug="ops",
                    display_name="Ops",
                    email="ops@test.local",
                    password="secret",
                )

                apply_bootstrap_admin(store, settings)

                user = store.get_user_by_email("ops@test.local")
                assert user is not None
                self.assertTrue(user.is_admin)

    def test_count_admins_excludes_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.create_user(
                    slug="aa",
                    display_name="A",
                    email="a@test.local",
                    password="x",
                    is_admin=True,
                )
                store.update_user(store.get_user_by_email("a@test.local").id, disabled=True)  # type: ignore[union-attr]
                self.assertEqual(store.count_admins(), 0)


class TestRegistrationPolicy(unittest.TestCase):
    def test_closed_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                self.assertFalse(registration_is_open())

    def test_open_when_env_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp), REGISTRATION_OPEN="true"):
                self.assertTrue(registration_is_open())


if __name__ == "__main__":
    unittest.main()
