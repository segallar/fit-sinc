"""Garmin upload duplicate (HTTP 409) handling."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
from garth.exc import GarthHTTPError
from getsync.garmin.upload_errors import (
    garmin_duplicate_log_message,
    is_garmin_duplicate_upload,
)
from getsync.state.store import Store
from getsync.sync.service import sync_activity
from helpers import isolated_env


class TestGarminDuplicateDetection(unittest.TestCase):
    def test_httpx_409(self) -> None:
        req = httpx.Request("POST", "https://example/upload")
        resp = httpx.Response(409, request=req)
        exc = httpx.HTTPStatusError("conflict", request=req, response=resp)
        self.assertTrue(is_garmin_duplicate_upload(exc))

    def test_garth_http_error_409(self) -> None:
        req = httpx.Request("POST", "https://example/upload")
        resp = httpx.Response(409, request=req)
        inner = httpx.HTTPStatusError("conflict", request=req, response=resp)
        exc = GarthHTTPError(msg="Error in request", error=inner)
        self.assertTrue(is_garmin_duplicate_upload(exc))

    def test_message_fallback(self) -> None:
        exc = RuntimeError("Garmin upload failed: Error in request: HTTP Error 409:")
        self.assertTrue(is_garmin_duplicate_upload(exc))

    def test_other_error_not_duplicate(self) -> None:
        self.assertFalse(is_garmin_duplicate_upload(RuntimeError("HTTP 500")))


class TestSyncGarminDuplicate(unittest.IsolatedAsyncioTestCase):
    async def test_409_marks_synced_and_logs_garmin_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with isolated_env(Path(tmp)):
                settings = __import__(
                    "getsync.config", fromlist=["get_settings"]
                ).get_settings()
                store = Store(settings.db_path)
                store.ensure_default_user(password="x")
                activity_id = "act-409-test"

                hh_meta = {
                    "name": "Evening Ride",
                    "createdAt": "2026-05-27T19:23:00Z",
                    "distance": 0,
                    "duration": 9,
                }

                with (
                    patch(
                        "getsync.sync.service.HammerheadClient",
                    ) as hh_cls,
                    patch(
                        "getsync.sync.service.upload_fit",
                        side_effect=GarthHTTPError(
                            msg="Error in request",
                            error=httpx.HTTPStatusError(
                                "409",
                                request=httpx.Request("POST", "https://x"),
                                response=httpx.Response(
                                    409, request=httpx.Request("POST", "https://x")
                                ),
                            ),
                        ),
                    ),
                ):
                    hh = hh_cls.return_value
                    hh.get_activity = AsyncMock(return_value=hh_meta)
                    hh.download_fit = AsyncMock(return_value=b"FIT")

                    result = await sync_activity(activity_id, user_id="default")

                self.assertEqual(result.status, "synced")
                self.assertIn("409", result.message)

                row = store.get_activity("default", activity_id)
                self.assertIsNotNone(row)
                assert row is not None
                self.assertEqual(row.sync_status, "synced")

                events = store.list_events(user_id="default", limit=10)
                types = [e.event_type for e in events]
                self.assertIn("garmin_duplicate", types)
                self.assertNotIn("error", types)
                dup = next(e for e in events if e.event_type == "garmin_duplicate")
                self.assertEqual(dup.message, garmin_duplicate_log_message())


if __name__ == "__main__":
    unittest.main()
