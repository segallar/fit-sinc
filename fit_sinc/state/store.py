import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ActivityRow:
    activity_id: str
    name: str | None
    activity_date: str | None
    distance: float | None
    duration: float | None
    sync_status: str
    fit_path: str | None
    synced_at: str | None
    error_message: str | None


@dataclass(frozen=True)
class SyncEventRow:
    id: int
    activity_id: str | None
    event_type: str
    message: str | None
    created_at: str


@dataclass(frozen=True)
class SyncIndexEntry:
    activity_id: str
    sync_status: str
    garmin_id: int | None
    garmin_upload_status: str | None
    fit_path: str | None
    synced_at: str | None
    error_message: str | None


@dataclass(frozen=True)
class SessionRefreshEventRow:
    id: int
    trigger: str
    event_type: str
    message: str | None
    created_at: str


class Store:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS activities (
                    activity_id TEXT PRIMARY KEY,
                    name TEXT,
                    activity_date TEXT,
                    distance REAL,
                    duration REAL,
                    sync_status TEXT NOT NULL DEFAULT 'pending',
                    fit_path TEXT,
                    garmin_result TEXT,
                    synced_at TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sync_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    activity_id TEXT,
                    event_type TEXT NOT NULL,
                    message TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_sync_events_created
                    ON sync_events(created_at DESC);

                CREATE TABLE IF NOT EXISTS session_refresh_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trigger TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_session_refresh_created
                    ON session_refresh_events(created_at DESC);
                """
            )

    def is_synced(self, activity_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT sync_status FROM activities WHERE activity_id = ?",
                (activity_id,),
            ).fetchone()
        return row is not None and row["sync_status"] == "synced"

    def upsert_activity(
        self,
        activity_id: str,
        *,
        name: str | None = None,
        activity_date: str | None = None,
        distance: float | None = None,
        duration: float | None = None,
        sync_status: str | None = None,
        fit_path: str | None = None,
        garmin_result: dict[str, Any] | str | None = None,
        synced_at: str | None = None,
        error_message: str | None = None,
    ) -> None:
        now = _utcnow()
        garmin_json = (
            json.dumps(garmin_result)
            if isinstance(garmin_result, dict)
            else garmin_result
        )
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT activity_id FROM activities WHERE activity_id = ?",
                (activity_id,),
            ).fetchone()
            if existing:
                fields: list[str] = ["updated_at = ?"]
                values: list[Any] = [now]
                for col, val in (
                    ("name", name),
                    ("activity_date", activity_date),
                    ("distance", distance),
                    ("duration", duration),
                    ("sync_status", sync_status),
                    ("fit_path", fit_path),
                    ("garmin_result", garmin_json),
                    ("synced_at", synced_at),
                    ("error_message", error_message),
                ):
                    if val is not None:
                        fields.append(f"{col} = ?")
                        values.append(val)
                values.append(activity_id)
                conn.execute(
                    f"UPDATE activities SET {', '.join(fields)} WHERE activity_id = ?",
                    values,
                )
            else:
                conn.execute(
                    """
                    INSERT INTO activities (
                        activity_id, name, activity_date, distance, duration,
                        sync_status, fit_path, garmin_result, synced_at, error_message,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        activity_id,
                        name,
                        activity_date,
                        distance,
                        duration,
                        sync_status or "pending",
                        fit_path,
                        garmin_json,
                        synced_at,
                        error_message,
                        now,
                        now,
                    ),
                )

    def mark_synced(
        self,
        activity_id: str,
        fit_path: str,
        garmin_result: dict[str, Any],
        *,
        name: str | None = None,
        activity_date: str | None = None,
        distance: float | None = None,
        duration: float | None = None,
    ) -> None:
        self.upsert_activity(
            activity_id,
            name=name,
            activity_date=activity_date,
            distance=distance,
            duration=duration,
            sync_status="synced",
            fit_path=fit_path,
            garmin_result=garmin_result,
            synced_at=_utcnow(),
            error_message=None,
        )

    def mark_error(self, activity_id: str, message: str) -> None:
        self.upsert_activity(
            activity_id,
            sync_status="error",
            error_message=message[:2000],
        )

    def log_event(
        self,
        event_type: str,
        message: str = "",
        activity_id: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO sync_events (activity_id, event_type, message, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (activity_id, event_type, message[:2000] or None, _utcnow()),
            )

    def list_activities(self, limit: int = 50) -> list[ActivityRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT activity_id, name, activity_date, distance, duration,
                       sync_status, fit_path, synced_at, error_message
                FROM activities
                ORDER BY COALESCE(activity_date, created_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            ActivityRow(
                activity_id=r["activity_id"],
                name=r["name"],
                activity_date=r["activity_date"],
                distance=r["distance"],
                duration=r["duration"],
                sync_status=r["sync_status"],
                fit_path=r["fit_path"],
                synced_at=r["synced_at"],
                error_message=r["error_message"],
            )
            for r in rows
        ]

    def get_activity(self, activity_id: str) -> ActivityRow | None:
        with self._conn() as conn:
            r = conn.execute(
                """
                SELECT activity_id, name, activity_date, distance, duration,
                       sync_status, fit_path, synced_at, error_message
                FROM activities WHERE activity_id = ?
                """,
                (activity_id,),
            ).fetchone()
        if not r:
            return None
        return ActivityRow(
            activity_id=r["activity_id"],
            name=r["name"],
            activity_date=r["activity_date"],
            distance=r["distance"],
            duration=r["duration"],
            sync_status=r["sync_status"],
            fit_path=r["fit_path"],
            synced_at=r["synced_at"],
            error_message=r["error_message"],
        )

    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[SyncEventRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, activity_id, event_type, message, created_at
                FROM sync_events
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [
            SyncEventRow(
                id=r["id"],
                activity_id=r["activity_id"],
                event_type=r["event_type"],
                message=r["message"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def count_events(self) -> int:
        with self._conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM sync_events").fetchone()
        return int(row["n"]) if row else 0

    @staticmethod
    def _garmin_id_from_result(raw: str | None) -> int | None:
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        activity_id = data.get("activity_id")
        if activity_id is not None:
            try:
                return int(activity_id)
            except (TypeError, ValueError):
                pass
        detail = data.get("detailedImportResult") or {}
        for key in ("successes", "failures"):
            for item in detail.get(key) or []:
                internal_id = item.get("internalId")
                if internal_id is not None:
                    try:
                        return int(internal_id)
                    except (TypeError, ValueError):
                        continue
        return None

    @staticmethod
    def _upload_status_from_result(raw: str | None) -> str | None:
        if not raw:
            return None
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict):
            status = data.get("status")
            return str(status) if status else None
        return None

    def build_sync_index(self) -> dict[str, SyncIndexEntry]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT activity_id, sync_status, garmin_result, fit_path,
                       synced_at, error_message
                FROM activities
                """
            ).fetchall()
        index: dict[str, SyncIndexEntry] = {}
        for r in rows:
            garmin_result = r["garmin_result"]
            index[r["activity_id"]] = SyncIndexEntry(
                activity_id=r["activity_id"],
                sync_status=r["sync_status"],
                garmin_id=self._garmin_id_from_result(garmin_result),
                garmin_upload_status=self._upload_status_from_result(garmin_result),
                fit_path=r["fit_path"],
                synced_at=r["synced_at"],
                error_message=r["error_message"],
            )
        return index

    def log_session_refresh(
        self,
        trigger: str,
        event_type: str,
        message: str = "",
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO session_refresh_events (trigger, event_type, message, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (trigger, event_type, message[:2000] or None, _utcnow()),
            )

    def list_session_refresh_events(
        self,
        limit: int = 100,
    ) -> list[SessionRefreshEventRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, trigger, event_type, message, created_at
                FROM session_refresh_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            SessionRefreshEventRow(
                id=r["id"],
                trigger=r["trigger"],
                event_type=r["event_type"],
                message=r["message"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
