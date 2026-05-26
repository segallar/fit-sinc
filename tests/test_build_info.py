"""Build metadata for footer and /health."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from getsync import __version__
from getsync.build_info import (
    build_footer_text,
    clear_build_info_cache,
    deploy_number,
    deploy_time_footer,
    git_commit_short,
)


class TestBuildInfo(unittest.TestCase):
    def tearDown(self) -> None:
        clear_build_info_cache()

    def test_build_footer_text_includes_version(self) -> None:
        self.assertIn(__version__, build_footer_text())

    def test_git_commit_from_env(self) -> None:
        import os

        prev = os.environ.get("GETSYNC_GIT_COMMIT")
        os.environ["GETSYNC_GIT_COMMIT"] = "abc123def456"
        try:
            self.assertEqual(git_commit_short(), "abc123def456")
            self.assertIn("abc123def456", build_footer_text())
        finally:
            clear_build_info_cache()
            if prev is None:
                os.environ.pop("GETSYNC_GIT_COMMIT", None)
            else:
                os.environ["GETSYNC_GIT_COMMIT"] = prev

    def test_deploy_meta_from_file(self) -> None:
        import getsync.build_info as bi

        with tempfile.TemporaryDirectory() as tmp:
            meta_path = Path(tmp) / "_build_meta.json"
            meta_path.write_text(
                json.dumps(
                    {
                        "commit": "deadbeef",
                        "deploy_number": 32,
                        "deployed_at": "2026-05-26T14:30:00Z",
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(bi, "_BUILD_META_FILE", meta_path):
                clear_build_info_cache()
                self.assertEqual(git_commit_short(), "deadbeef")
                self.assertEqual(deploy_number(), 32)
                self.assertEqual(deploy_time_footer(), "26.05.2026 14:30 UTC")
                text = build_footer_text()
                self.assertIn("deploy #32", text)
                self.assertIn("26.05.2026 14:30 UTC", text)

    def test_health_includes_deploy_fields(self) -> None:
        from fastapi.testclient import TestClient

        from getsync.web.app import app

        data = TestClient(app).get("/health").json()
        self.assertEqual(data["version"], __version__)
        self.assertTrue(data["commit"])
        self.assertIn("deploy_number", data)
        self.assertIn("deployed_at", data)

    def test_home_footer_shows_version(self) -> None:
        from fastapi.testclient import TestClient

        from getsync.web.app import app

        r = TestClient(app).get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(f"GetSync v{__version__}", r.text)

    def test_jinja_footer_renders_commit_strings(self) -> None:
        from getsync.web.templating import render_template

        html = render_template("components/build_footer.html")
        self.assertIn(f"GetSync v{__version__}", html)
        self.assertNotIn("lru_cache", html)
        self.assertNotIn("function deploy_number", html)
        self.assertNotIn("function deploy_time_footer", html)
