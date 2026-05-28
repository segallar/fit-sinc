"""Map catalog rows to browse presentation rows."""

from __future__ import annotations

from getsync.contracts.activities import NormalizedActivity
from getsync.contracts.persistence import SyncIndexEntry
from getsync.workspace.domain.rows import ActivityBrowseRow


def _hh_sync_labels(entry: SyncIndexEntry | None) -> tuple[str, str | None]:
    if entry is None:
        return "not synced", None
    detail = entry.garmin_upload_status
    if entry.sync_status == "synced":
        return "synced", detail
    if entry.sync_status == "error":
        return "error", entry.error_message
    if entry.sync_status == "pending":
        return "pending", None
    return entry.sync_status, detail


def _garmin_sync_labels(
    entry: SyncIndexEntry | None,
) -> tuple[str, str | None, str | None]:
    if entry is None:
        return "not synced", None, None
    detail = entry.garmin_upload_status
    if entry.sync_status == "synced":
        return "synced", detail, entry.activity_id
    if entry.sync_status == "error":
        return "error", entry.error_message, entry.activity_id
    return entry.sync_status, detail, entry.activity_id


def normalized_to_browse_row(
    row: NormalizedActivity,
    index: dict[str, SyncIndexEntry],
    by_garmin: dict[int, SyncIndexEntry],
) -> ActivityBrowseRow:
    """Map catalog NormalizedActivity to browse row."""
    if row.source == "hammerhead":
        entry = index.get(row.activity_id)
        status, detail = _hh_sync_labels(entry)
        if entry is None:
            status = row.sync_status or "not synced"
            detail = None
        garmin_id = entry.garmin_id if entry else None
        fit_available = bool((entry and entry.storage_key) or row.storage_key)
        return ActivityBrowseRow(
            source="hammerhead",
            external_id=row.activity_id,
            name=row.name or "—",
            activity_date=row.activity_date,
            distance=row.distance,
            duration=row.duration,
            activity_type=row.activity_type,
            sync_status=status,
            sync_detail=detail,
            hammerhead_id=row.activity_id,
            garmin_id=garmin_id,
            fit_available=fit_available,
        )

    try:
        garmin_id = int(row.activity_id)
    except (TypeError, ValueError):
        garmin_id = None
    entry = by_garmin.get(garmin_id) if garmin_id is not None else None
    status, detail, hh_id = _garmin_sync_labels(entry)
    if entry is None:
        status = row.sync_status or "not synced"
        detail = None
        hh_id = None
    fit_available = bool(entry and entry.storage_key)
    return ActivityBrowseRow(
        source="garmin",
        external_id=row.activity_id,
        name=row.name or "—",
        activity_date=row.activity_date,
        distance=row.distance,
        duration=row.duration,
        activity_type=row.activity_type,
        sync_status=status,
        sync_detail=detail,
        hammerhead_id=hh_id,
        garmin_id=garmin_id,
        fit_available=fit_available,
    )


def catalog_row_to_browse_row(
    row: NormalizedActivity,
    index: dict[str, SyncIndexEntry],
    by_garmin: dict[int, SyncIndexEntry],
) -> ActivityBrowseRow:
    """Alias for normalized_to_browse_row (backward compat)."""
    return normalized_to_browse_row(row, index, by_garmin)
