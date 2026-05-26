"""User locale in DB and settings UI."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from getsync.state.store import Store
from getsync.users.locale import DEFAULT_LOCALE
from getsync.web.site_i18n import LANG_COOKIE
from helpers import isolated_env


class TestUserLocale(unittest.TestCase):
    def test_create_user_default_locale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                user = store.create_user(
                    slug="athlete",
                    display_name="Athlete",
                    email="a@test.local",
                    password="password1",
                )
                self.assertEqual(user.locale, DEFAULT_LOCALE)

    def test_settings_save_locale_russian_nav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.ensure_default_user(
                    email="owner@test.local",
                    password="good-pass",
                )

                from getsync.web.app import app

                client = TestClient(app)
                client.post(
                    "/app/login",
                    data={"email": "owner@test.local", "password": "good-pass"},
                    follow_redirects=False,
                )
                r = client.post(
                    "/app/settings/profile",
                    data={
                        "display_name": "Roman",
                        "email": "owner@test.local",
                        "telegram": "",
                        "timezone": "Europe/Moscow",
                        "locale": "ru",
                    },
                    follow_redirects=False,
                )
                self.assertEqual(r.status_code, 303)
                self.assertEqual(r.cookies.get(LANG_COOKIE), "ru")

                user = store.get_user("default")
                assert user is not None
                self.assertEqual(user.locale, "ru")

                page = client.get("/app/settings")
                self.assertIn("Настройки", page.text)
                self.assertIn("Язык интерфейса", page.text)

                dash = client.get("/app/activities")
                self.assertIn("Активности", dash.text)
