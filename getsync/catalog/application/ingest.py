"""Persist provider metadata into the activity catalog."""

from __future__ import annotations

from collections.abc import Iterable

from getsync.contracts.activities import NormalizedActivity
from getsync.contracts.persistence import ActivityCatalog


def persist_normalized_rows(
    catalog: ActivityCatalog,
    rows: Iterable[NormalizedActivity],
) -> int:
    """Upsert metadata + sync status from ingest; preserve FIT/Garmin on HH rows."""
    n = 0
    for row in rows:
        catalog.upsert_from_normalized(row)
        n += 1
    return n
