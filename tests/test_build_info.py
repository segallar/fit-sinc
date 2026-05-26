"""Build metadata for footer and /health."""

from __future__ import annotations

import unittest

from getsync import __version__
from getsync.build_info import build_footer_text, git_commit_short


class TestBuildInfo(unittest.TestCase):
    def test_build_footer_text_includes_version(self) -> None:
        self.assertIn(__version__, build_footer_text())

    def test_git_commit_from_env(self) -> None:
        import os

        git_commit_short.cache_clear()
        prev = os.environ.get("GETSYNC_GIT_COMMIT")
        os.environ["GETSYNC_GIT_COMMIT"] = "abc123def456"
        try:
            self.assertEqual(git_commit_short(), "abc123def456")
            self.assertIn("abc123def456", build_footer_text())
        finally:
            git_commit_short.cache_clear()
            if prev is None:
                os.environ.pop("GETSYNC_GIT_COMMIT", None)
            else:
                os.environ["GETSYNC_GIT_COMMIT"] = prev

    def test_health_includes_commit(self) -> None:
        from fastapi.testclient import TestClient

        from getsync.web.app import app

        client = TestClient(app)
        data = client.get("/health").json()
        self.assertEqual(data["version"], __version__)
        self.assertTrue(data["commit"])

    def test_home_footer_shows_version(self) -> None:
        from fastapi.testclient import TestClient

        from getsync.web.app import app

        r = TestClient(app).get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(f"GetSync v{__version__}", r.text)
