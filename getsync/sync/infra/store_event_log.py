"""Sync event log adapter (sync_events table owner)."""

from __future__ import annotations

from getsync.state.store import Store


class StoreSyncEventLog:
    def __init__(self, store: Store) -> None:
        self._store = store

    def append(
        self,
        event_type: str,
        message: str,
        activity_id: str | None = None,
        *,
        user_id: str | None = None,
    ) -> None:
        self._store.log_event(event_type, message, activity_id, user_id=user_id)
