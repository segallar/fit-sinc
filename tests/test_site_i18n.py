"""Landing page language (EN default, RU optional)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from getsync.web.site_i18n import DEFAULT_LANG, LANG_COOKIE
from helpers import isolated_env


class TestSiteI18n(unittest.TestCase):
    def test_home_default_english(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                r = TestClient(app).get("/", follow_redirects=False)
                self.assertEqual(r.status_code, 200)
                self.assertIn("All your workouts in one place", r.text)
                self.assertIn("Sign up", r.text)
                self.assertIn("/app/login", r.text)

    def test_home_russian_via_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                r = TestClient(app).get("/?lang=ru", follow_redirects=False)
                self.assertEqual(r.status_code, 200)
                self.assertIn("Все ваши тренировки", r.text)
                self.assertEqual(r.cookies.get(LANG_COOKIE), "ru")

    def test_home_russian_via_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                client = TestClient(app)
                client.get("/?lang=ru")
                r = client.get("/")
                self.assertIn("Все ваши тренировки", r.text)

    def test_set_lang_redirect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                from getsync.web.app import app

                client = TestClient(app)
                r = client.get("/set-lang?lang=ru&next=/", follow_redirects=False)
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.cookies.get(LANG_COOKIE), "ru")

    def test_default_lang_constant(self) -> None:
        self.assertEqual(DEFAULT_LANG, "en")
