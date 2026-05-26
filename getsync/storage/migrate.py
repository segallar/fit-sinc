"""Move legacy FIT files into per-user activities/ layout."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from getsync.state.store import Store
from getsync.storage.activity import ActivityStorage
from getsync.storage.keys import build_object_key
from getsync.users.context import resolve_user_context

logger = logging.getLogger("getsync.storage.migrate")


def migrate_user_fit_files(store: Store, user_id: str) -> int:
    """
    Copy fits/*.fit → activities/hammerhead/{id}.fit and set storage_key.
    Idempotent: skips when storage_key already set and target exists.
    """
    ctx = resolve_user_context(user_id)
    storage = ActivityStorage(ctx)
    legacy_dir = storage.legacy_fits_dir()
    if not legacy_dir.is_dir():
        return 0

    moved = 0
    for path in legacy_dir.glob("*.fit"):
        external_id = path.stem
        key = build_object_key("hammerhead", external_id, kind="fit")
        target = storage.open_fit_path(key)
        if target is None or not target.is_file():
            storage.put_fit("hammerhead", external_id, path.read_bytes())
        row = store.get_activity(user_id, external_id, source="hammerhead")
        if row is None:
            continue
        if not row.storage_key:
            store.upsert_activity(
                user_id,
                external_id,
                source="hammerhead",
                storage_key=key,
            )
            moved += 1
    return moved


def migrate_legacy_fit_path_column(store: Store, user_id: str) -> int:
    """Set storage_key from absolute fit_path when file still exists."""
    updated = 0
    for row in store.list_activities(user_id, limit=10_000):
        if row.storage_key or not row.fit_path:
            continue
        fit_path = Path(row.fit_path)
        if not fit_path.is_file():
            continue
        storage = ActivityStorage(resolve_user_context(user_id))
        if not storage.has_fit(
            key := build_object_key(row.source, row.activity_id, kind="fit")
        ):
            storage.put_fit(row.source, row.activity_id, fit_path.read_bytes())
        store.upsert_activity(
            user_id,
            row.activity_id,
            source=row.source,
            storage_key=key,
        )
        updated += 1
    return updated
