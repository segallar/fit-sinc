"""Persist activity catalog rows (backward compat shim)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from getsync.catalog.application.ingest import persist_normalized_rows
from getsync.catalog.infra.store_catalog import StoreCatalog
from getsync.contracts.activities import NormalizedActivity
from getsync.state.store import Store


def persist_browse_rows(
    store: Store,
    user_id: str,
    rows: Iterable[Any],
) -> int:
    """Upsert metadata + sync status from browse; preserve FIT/Garmin result on HH rows."""
    catalog = StoreCatalog(store)
    normalized = [
        NormalizedActivity(
            user_id=user_id,
            source=row.source,
            activity_id=row.external_id,
            name=row.name,
            activity_date=row.activity_date,
            distance=row.distance,
            duration=row.duration,
            activity_type=row.activity_type,
            sync_status=row.sync_status,
        )
        for row in rows
    ]
    return persist_normalized_rows(catalog, normalized)
