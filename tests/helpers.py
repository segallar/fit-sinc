"""Shared test utilities (no network)."""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import os
from pathlib import Path
from typing import Iterator

from fit_sinc.config import get_settings


def webhook_hmac(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@contextlib.contextmanager
def isolated_env(tmp_root: Path, **extra: str) -> Iterator[Path]:
    """Temp DATA_DIR and env; clears get_settings cache on exit."""
    data_dir = tmp_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    overrides: dict[str, str] = {
        "DATA_DIR": str(data_dir),
        "HAMMERHEAD_WEBHOOK_SECRET": "test-webhook-secret",
        "SESSION_SECRET": "test-session-secret-for-unittest",
        "DEFAULT_USER_ID": "default",
        "REGISTRATION_OPEN": "false",
        **extra,
    }
    saved: dict[str, str | None] = {}
    for key, value in overrides.items():
        saved[key] = os.environ.get(key)
        os.environ[key] = value
    get_settings.cache_clear()
    try:
        yield data_dir
    finally:
        get_settings.cache_clear()
        for key, prev in saved.items():
            if prev is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = prev
