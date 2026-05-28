"""Scan a registered source into normalized catalog rows."""

from __future__ import annotations

from getsync.contracts.activities import ActivitySource, NormalizedActivity
from getsync.contracts.persistence import ActivityCatalog, SyncIndexEntry
from getsync.providers.registry import get_source
from getsync.users.context import UserContext

MAX_SCAN_PAGES = 25
SCAN_BATCH = 100


def _apply_hammerhead_sync_status(
    rows: list[NormalizedActivity],
    index: dict[str, SyncIndexEntry],
) -> list[NormalizedActivity]:
    out: list[NormalizedActivity] = []
    for row in rows:
        entry = index.get(row.activity_id)
        status = entry.sync_status if entry else row.sync_status
        out.append(
            NormalizedActivity(
                user_id=row.user_id,
                source=row.source,
                activity_id=row.activity_id,
                name=row.name,
                activity_date=row.activity_date,
                distance=row.distance,
                duration=row.duration,
                activity_type=row.activity_type,
                sync_status=status,
            )
        )
    return out


def _apply_garmin_sync_status(
    rows: list[NormalizedActivity],
    index: dict[str, SyncIndexEntry],
) -> list[NormalizedActivity]:
    by_garmin = {entry.garmin_id: entry for entry in index.values() if entry.garmin_id}
    out: list[NormalizedActivity] = []
    for row in rows:
        try:
            garmin_id = int(row.activity_id)
        except (TypeError, ValueError):
            garmin_id = None
        entry = by_garmin.get(garmin_id) if garmin_id is not None else None
        status = entry.sync_status if entry else row.sync_status
        out.append(
            NormalizedActivity(
                user_id=row.user_id,
                source=row.source,
                activity_id=row.activity_id,
                name=row.name,
                activity_date=row.activity_date,
                distance=row.distance,
                duration=row.duration,
                activity_type=row.activity_type,
                sync_status=status,
            )
        )
    return out


async def scan_source(
    source_id: str,
    catalog: ActivityCatalog,
    ctx: UserContext,
    *,
    max_pages: int = MAX_SCAN_PAGES,
    per_page: int = SCAN_BATCH,
) -> list[NormalizedActivity]:
    """Fetch all pages from a registered ActivitySource and enrich sync status."""
    source: ActivitySource = get_source(source_id)
    if source_id == "hammerhead":
        from getsync.hammerhead.client import HammerheadClient

        if HammerheadClient(ctx).load_tokens() is None:
            return []
    elif source_id == "strava":
        if not source.connection_status(ctx).connected:
            return []
    rows: list[NormalizedActivity] = []
    page = 1
    total_pages = 1
    while page <= total_pages and page <= max_pages:
        result = await source.fetch_page(ctx, page=page, per_page=per_page)
        rows.extend(result.items)
        total_pages = max(1, result.total_pages)
        if not result.items:
            break
        page += 1
    index = catalog.build_sync_index(ctx.user_id)
    if source_id == "hammerhead":
        return _apply_hammerhead_sync_status(rows, index)
    if source_id == "garmin":
        return _apply_garmin_sync_status(rows, index)
    return rows
