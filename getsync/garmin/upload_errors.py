"""Garmin upload duplicate detection (HTTP 409 / import already exists)."""

from __future__ import annotations

from typing import Any

import httpx

try:
    from garth.exc import GarthHTTPError as _GarthHTTPError
except ImportError:  # pragma: no cover
    _GarthHTTPError = None  # type: ignore[misc, assignment]


def garmin_duplicate_result() -> dict[str, Any]:
    return {"status": "duplicate"}


def garmin_duplicate_log_message() -> str:
    return "Activity already in Garmin Connect (HTTP 409, duplicate)"


def _http_status_from_exc(exc: BaseException) -> int | None:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code
    if _GarthHTTPError is not None and isinstance(exc, _GarthHTTPError):
        err = getattr(exc, "error", None)
        resp = getattr(err, "response", None)
        if resp is not None:
            return getattr(resp, "status_code", None)
    return None


def is_garmin_duplicate_upload(exc: BaseException) -> bool:
    if _http_status_from_exc(exc) == 409:
        return True
    text = str(exc).lower()
    return "409" in text and (
        "duplicate" in text
        or "upload" in text
        or "error in request" in text
    )
