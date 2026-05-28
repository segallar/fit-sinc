"""Staging smoke (PLAN 2.13 tier C). Skipped unless GETSYNC_E2E_BASE_URL is set."""

from __future__ import annotations

import os
import unittest

import httpx

_BASE = os.environ.get("GETSYNC_E2E_BASE_URL", "").rstrip("/")


@unittest.skipIf(not _BASE, "GETSYNC_E2E_BASE_URL unset")
class TestStagingSmoke(unittest.TestCase):
    def test_health(self) -> None:
        r = httpx.get(f"{_BASE}/health", timeout=15.0)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data.get("service"), "getsync")
        self.assertIn("version", data)

    def test_login_page(self) -> None:
        r = httpx.get(f"{_BASE}/app/login", timeout=15.0)
        self.assertEqual(r.status_code, 200)
        self.assertIn("login", r.text.lower())
