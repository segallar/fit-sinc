"""Persist activity catalog rows to SQLite (all sources)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from getsync.state.store import Store


def persist_browse_rows(
    store: Store,
    user_id: str,
    rows: Iterable[Any],
) -> int:
    """Upsert metadata + sync status from browse; preserve FIT/Garmin result on HH rows."""
    n = 0
    for row in rows:
        store.upsert_activity(
            user_id,
            row.external_id,
            source=row.source,
            name=row.name,
            activity_date=row.activity_date,
            distance=row.distance,
            duration=row.duration,
            activity_type=row.activity_type,
            sync_status=row.sync_status,
        )
        n += 1
    return n
