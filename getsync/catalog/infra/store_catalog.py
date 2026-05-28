"""Store-backed ActivityCatalog adapter (single writer for activities table)."""

from __future__ import annotations

from typing import Any

from getsync.contracts.activities import NormalizedActivity
from getsync.contracts.persistence import SyncIndexEntry
from getsync.state.store import ActivityRow, Store


def _row_to_normalized(row: ActivityRow) -> NormalizedActivity:
    return NormalizedActivity(
        user_id=row.user_id,
        source=row.source,
        activity_id=row.activity_id,
        name=row.name,
        activity_date=row.activity_date,
        distance=row.distance,
        duration=row.duration,
        activity_type=row.activity_type,
        sync_status=row.sync_status,
        storage_key=row.storage_key,
    )


class StoreCatalog:
    """ActivityCatalog port implementation delegating to Store."""

    def __init__(self, store: Store) -> None:
        self._store = store

    def upsert_activity(
        self,
        user_id: str,
        activity_id: str,
        *,
        source: str = "hammerhead",
        **fields: Any,
    ) -> None:
        self._store.upsert_activity(user_id, activity_id, source=source, **fields)

    def mark_synced(
        self,
        user_id: str,
        activity_id: str,
        garmin_result: dict[str, Any] | None,
        *,
        storage_key: str | None = None,
        **meta: Any,
    ) -> None:
        if garmin_result is None:
            self._store.upsert_activity(
                user_id,
                activity_id,
                sync_status="synced",
                storage_key=storage_key,
                **meta,
            )
            return
        assert storage_key is not None
        self._store.mark_synced(
            user_id,
            activity_id,
            garmin_result,
            storage_key=storage_key,
            **meta,
        )

    def mark_error(self, user_id: str, activity_id: str, message: str) -> None:
        self._store.mark_error(user_id, activity_id, message)

    def is_synced(self, user_id: str, activity_id: str) -> bool:
        return self._store.is_synced(user_id, activity_id)

    def build_sync_index(self, user_id: str) -> dict[str, SyncIndexEntry]:
        raw = self._store.build_sync_index(user_id)
        return {
            activity_id: SyncIndexEntry(
                activity_id=entry.activity_id,
                sync_status=entry.sync_status,
                garmin_id=entry.garmin_id,
                garmin_upload_status=entry.garmin_upload_status,
                storage_key=entry.storage_key,
                synced_at=entry.synced_at,
                error_message=entry.error_message,
            )
            for activity_id, entry in raw.items()
        }

    def list_for_browse(
        self,
        user_id: str,
        *,
        source: str | None = None,
    ) -> tuple[NormalizedActivity, ...]:
        rows = self._store.list_activity_catalog(user_id, source=source)
        return tuple(_row_to_normalized(row) for row in rows)

    def list_for_calendar(
        self,
        user_id: str,
        *,
        source: str | None = None,
    ) -> tuple[NormalizedActivity, ...]:
        rows = self._store.list_activity_catalog_for_calendar(user_id, source=source)
        return tuple(_row_to_normalized(row) for row in rows)

    def upsert_from_normalized(self, activity: NormalizedActivity) -> None:
        self._store.upsert_activity(
            activity.user_id,
            activity.activity_id,
            source=activity.source,
            name=activity.name,
            activity_date=activity.activity_date,
            distance=activity.distance,
            duration=activity.duration,
            activity_type=activity.activity_type,
            sync_status=activity.sync_status,
            storage_key=activity.storage_key,
        )
