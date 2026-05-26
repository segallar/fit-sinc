"""Migrate v1 flat data/ layout to data/users/{id}/."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from getsync.config import Settings
from getsync.storage import load_json

logger = logging.getLogger("getsync.users.migrate")

_LEGACY_NAMES = (
    "hammerhead_tokens.json",
    "garth",
    "garmin_web",
    "fits",
)


def migrate_legacy_files(settings: Settings, user_id: str) -> None:
    """Move data/* tenant files into data/users/{user_id}/ if still at root."""
    root = settings.data_dir
    dest = root / "users" / user_id
    dest.mkdir(parents=True, exist_ok=True)

    for name in _LEGACY_NAMES:
        src = root / name
        if not src.exists():
            continue
        target = dest / name
        if target.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, target)
            logger.info("copied %s -> %s", src, target)
        else:
            shutil.copy2(src, target)
            logger.info("copied %s -> %s", src, target)


def infer_hammerhead_user_id(settings: Settings) -> str | None:
    data = load_json(settings.data_dir / "hammerhead_tokens.json")
    if not data:
        legacy = settings.data_dir / "users" / "default" / "hammerhead_tokens.json"
        data = load_json(legacy)
    if not data:
        return None
    uid = data.get("user_id")
    return str(uid) if uid else None
