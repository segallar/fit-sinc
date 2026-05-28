"""Persistence ports: single-writer per SQLite table (see docs/MODULES.md §2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from getsync.contracts.activities import NormalizedActivity


@dataclass(frozen=True)
class SyncIndexEntry:
    """Sync pipeline index row for browse UI (workspace view)."""

    activity_id: str
    sync_status: str
    garmin_id: int | None
    garmin_upload_status: str | None
    storage_key: str | None
    synced_at: str | None
    error_message: str | None


class ActivityCatalog(Protocol):
    """Owner: catalog module — `activities` table."""

    def upsert_activity(
        self,
        user_id: str,
        activity_id: str,
        *,
        source: str = "hammerhead",
        **fields: Any,
    ) -> None: ...

    def mark_synced(
        self,
        user_id: str,
        activity_id: str,
        garmin_result: dict[str, Any] | None,
        *,
        storage_key: str | None = None,
        **meta: Any,
    ) -> None: ...

    def mark_error(self, user_id: str, activity_id: str, message: str) -> None: ...

    def is_synced(self, user_id: str, activity_id: str) -> bool: ...

    def build_sync_index(self, user_id: str) -> dict[str, SyncIndexEntry]: ...

    def list_for_browse(
        self,
        user_id: str,
        *,
        source: str | None = None,
    ) -> tuple[NormalizedActivity, ...]: ...

    def list_for_calendar(
        self,
        user_id: str,
        *,
        source: str | None = None,
    ) -> tuple[NormalizedActivity, ...]: ...

    def upsert_from_normalized(self, activity: NormalizedActivity) -> None: ...


class SyncEventLog(Protocol):
    """Owner: sync module — `sync_events` table."""

    def append(
        self,
        event_type: str,
        message: str,
        activity_id: str | None = None,
        *,
        user_id: str | None = None,
    ) -> None: ...


class GarminSessionLog(Protocol):
    """Owner: providers/garmin — `session_refresh_events` table."""

    def append(
        self,
        user_id: str | None,
        trigger: str,
        event_type: str,
        message: str | None = None,
    ) -> None: ...


class UserRepository(Protocol):
    """Owner: users module — `users` table."""

    def get_user(self, user_id: str) -> Any | None: ...

    def get_user_by_hammerhead_id(self, hammerhead_user_id: str) -> Any | None: ...


class AuditLog(Protocol):
    """Owner: users module — `admin_audit_events` table."""

    def append(
        self,
        *,
        user_id: str | None,
        action: str,
        message: str,
        ip: str | None = None,
    ) -> None: ...
