"""Activity storage layout and StorageBackend."""

import tempfile
import unittest
from pathlib import Path

from getsync.storage.activity import ActivityStorage
from getsync.storage.backend import LocalFilesystemBackend
from getsync.storage.keys import build_object_key
from getsync.users.context import UserContext
from helpers import isolated_env


class TestStorage(unittest.TestCase):
    def test_build_object_key(self) -> None:
        key = build_object_key("hammerhead", "ride/42", kind="fit")
        self.assertEqual(key, "activities/hammerhead/ride_42.fit")

    def test_local_backend_per_user_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.config import get_settings

                settings = get_settings()
                ctx = UserContext(user_id="alice", settings=settings)
                storage = ActivityStorage(ctx)
                key = storage.put_fit("hammerhead", "act-1", b"FITDATA")
                self.assertTrue(key.startswith("activities/hammerhead/"))
                path = storage.open_fit_path(key)
                self.assertIsNotNone(path)
                assert path is not None
                self.assertEqual(path.read_bytes(), b"FITDATA")
                self.assertIn(
                    "users/alice/activities/hammerhead",
                    str(path).replace("\\", "/"),
                )

    def test_backend_isolation_between_users(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            backend = LocalFilesystemBackend(root)
            backend.put("u1", "activities/hammerhead/a.fit", b"one")
            backend.put("u2", "activities/hammerhead/a.fit", b"two")
            self.assertEqual(backend.open_path("u1", "activities/hammerhead/a.fit").read_bytes(), b"one")
            self.assertEqual(backend.open_path("u2", "activities/hammerhead/a.fit").read_bytes(), b"two")


if __name__ == "__main__":
    unittest.main()
