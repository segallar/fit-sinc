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

    from getsync.config import get_settings
    from getsync.state.store import Store
    from getsync.storage.migrate import (
        migrate_legacy_fit_path_column,
        migrate_user_fit_files,
    )

    store = Store(get_settings().db_path)
    n = migrate_user_fit_files(store, user_id)
    if n:
        logger.info("migrated %s FIT files to activities/ for user %s", n, user_id)
    n2 = migrate_legacy_fit_path_column(store, user_id)
    if n2:
        logger.info("set storage_key on %s activities for user %s", n2, user_id)


def infer_hammerhead_user_id(settings: Settings) -> str | None:
    data = load_json(settings.data_dir / "hammerhead_tokens.json")
    if not data:
        legacy = settings.data_dir / "users" / "default" / "hammerhead_tokens.json"
        data = load_json(legacy)
    if not data:
        return None
    uid = data.get("user_id")
    return str(uid) if uid else None
