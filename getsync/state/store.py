import json
import logging
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from getsync.users.models import UserRow
from getsync.users.passwords import hash_password
from getsync.users.locale import DEFAULT_LOCALE, normalize_locale
from getsync.users.timezones import DEFAULT_TIMEZONE, normalize_timezone

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")

_audit_log = logging.getLogger("getsync.audit")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ActivityRow:
    user_id: str
    source: str
    activity_id: str
    name: str | None
    activity_date: str | None
    distance: float | None
    duration: float | None
    activity_type: str | None
    sync_status: str
    storage_key: str | None
    synced_at: str | None
    error_message: str | None


@dataclass(frozen=True)
class SyncEventRow:
    id: int
    user_id: str | None
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
    storage_key: str | None
    synced_at: str | None
    error_message: str | None


@dataclass(frozen=True)
class SessionRefreshEventRow:
    id: int
    user_id: str | None
    trigger: str
    event_type: str
    message: str | None
    created_at: str


@dataclass(frozen=True)
class AdminLogRow:
    """Unified admin log entry (sync, Garmin JWT, admin audit)."""

    created_at: str
    user_id: str | None
    log_kind: str  # sync | garmin | admin
    event_type: str
    subject: str | None
    message: str | None


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

    def _table_has_column(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(r["name"] == column for r in rows)

    @staticmethod
    def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None

    def _init_schema(self) -> None:
        """Create schema; migrate v1 DB before indexes that reference user_id."""
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    slug TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    telegram TEXT,
                    timezone TEXT NOT NULL DEFAULT 'Europe/Moscow',
                    locale TEXT NOT NULL DEFAULT 'en',
                    hammerhead_user_id TEXT UNIQUE,
                    password_hash TEXT NOT NULL,
                    disabled INTEGER NOT NULL DEFAULT 0,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._ensure_users_admin_column(conn)
            self._ensure_users_locale_column(conn)
            self._ensure_activities_table(conn)
            self._ensure_sync_events_table(conn)
            self._ensure_session_refresh_table(conn)
            self._ensure_admin_audit_table(conn)
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_activities_user_date
                    ON activities(user_id, activity_date DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sync_events_created
                    ON sync_events(created_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_session_refresh_created
                    ON session_refresh_events(created_at DESC)
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_admin_audit_created
                    ON admin_audit_events(created_at DESC)
                """
            )

    def _ensure_users_admin_column(self, conn: sqlite3.Connection) -> None:
        if not self._table_has_column(conn, "users", "is_admin"):
            conn.execute(
                "ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0"
            )

    def _ensure_users_locale_column(self, conn: sqlite3.Connection) -> None:
        if not self._table_has_column(conn, "users", "locale"):
            conn.execute(
                "ALTER TABLE users ADD COLUMN locale TEXT NOT NULL DEFAULT 'en'"
            )

    def count_admins(self) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM users WHERE is_admin = 1 AND disabled = 0"
            ).fetchone()
        return int(row["n"]) if row else 0

    def set_admin(self, user_id: str, *, is_admin: bool = True) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET is_admin = ?, updated_at = ? WHERE id = ?",
                (1 if is_admin else 0, _utcnow(), user_id),
            )

    def _ensure_activities_table(self, conn: sqlite3.Connection) -> None:
        if self._table_exists(conn, "activities"):
            if not self._table_has_column(conn, "activities", "user_id"):
                self._migrate_activities_v1(conn)
            if not self._table_has_column(conn, "activities", "source"):
                self._migrate_activities_add_source(conn)
            elif not self._table_has_column(conn, "activities", "activity_type"):
                conn.execute("ALTER TABLE activities ADD COLUMN activity_type TEXT")
            if not self._table_has_column(conn, "activities", "storage_key"):
                conn.execute("ALTER TABLE activities ADD COLUMN storage_key TEXT")
            return
        conn.execute(
            """
            CREATE TABLE activities (
                user_id TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'hammerhead',
                activity_id TEXT NOT NULL,
                name TEXT,
                activity_date TEXT,
                distance REAL,
                duration REAL,
                activity_type TEXT,
                sync_status TEXT NOT NULL DEFAULT 'pending',
                storage_key TEXT,
                fit_path TEXT,
                garmin_result TEXT,
                synced_at TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, source, activity_id)
            )
            """
        )

    def _migrate_activities_add_source(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE activities_catalog (
                user_id TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'hammerhead',
                activity_id TEXT NOT NULL,
                name TEXT,
                activity_date TEXT,
                distance REAL,
                duration REAL,
                activity_type TEXT,
                sync_status TEXT NOT NULL DEFAULT 'pending',
                storage_key TEXT,
                fit_path TEXT,
                garmin_result TEXT,
                synced_at TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (user_id, source, activity_id)
            )
            """
        )
        conn.execute(
            """
            INSERT INTO activities_catalog (
                user_id, source, activity_id, name, activity_date, distance, duration,
                activity_type, sync_status, storage_key, fit_path, garmin_result, synced_at,
                error_message, created_at, updated_at
            )
            SELECT
                user_id, 'hammerhead', activity_id, name, activity_date, distance, duration,
                NULL, sync_status, NULL, fit_path, garmin_result, synced_at,
                error_message, created_at, updated_at
            FROM activities
            """
        )
        conn.execute("DROP TABLE activities")
        conn.execute("ALTER TABLE activities_catalog RENAME TO activities")
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_activities_user_date
                ON activities(user_id, activity_date DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_activities_user_source_date
                ON activities(user_id, source, activity_date DESC)
            """
        )

    def _ensure_sync_events_table(self, conn: sqlite3.Connection) -> None:
        if not self._table_exists(conn, "sync_events"):
            conn.execute(
                """
                CREATE TABLE sync_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    activity_id TEXT,
                    event_type TEXT NOT NULL,
                    message TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            return
        if not self._table_has_column(conn, "sync_events", "user_id"):
            conn.execute("ALTER TABLE sync_events ADD COLUMN user_id TEXT")
            conn.execute(
                """
                UPDATE sync_events SET user_id = (
                    SELECT user_id FROM activities
                    WHERE activities.activity_id = sync_events.activity_id
                    LIMIT 1
                )
                WHERE user_id IS NULL
                """
            )
            conn.execute("UPDATE sync_events SET user_id = 'default' WHERE user_id IS NULL")

    def _ensure_session_refresh_table(self, conn: sqlite3.Connection) -> None:
        if not self._table_exists(conn, "session_refresh_events"):
            conn.execute(
                """
                CREATE TABLE session_refresh_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    trigger TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    message TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            return
        if not self._table_has_column(conn, "session_refresh_events", "user_id"):
            conn.execute("ALTER TABLE session_refresh_events ADD COLUMN user_id TEXT")
            conn.execute(
                "UPDATE session_refresh_events SET user_id = 'default' WHERE user_id IS NULL"
            )

    def _ensure_admin_audit_table(self, conn: sqlite3.Connection) -> None:
        if not self._table_exists(conn, "admin_audit_events"):
            conn.execute(
                """
                CREATE TABLE admin_audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    actor_user_id TEXT,
                    event_type TEXT NOT NULL,
                    subject TEXT,
                    message TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def _migrate_activities_v1(self, conn: sqlite3.Connection) -> None:
        if not self._table_has_column(conn, "activities", "user_id"):
            conn.execute(
                """
                CREATE TABLE activities_v2 (
                    user_id TEXT NOT NULL DEFAULT 'default',
                    activity_id TEXT NOT NULL,
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
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, activity_id)
                )
                """
            )
            conn.execute(
                """
                INSERT INTO activities_v2 (
                    user_id, activity_id, name, activity_date, distance, duration,
                    sync_status, fit_path, garmin_result, synced_at, error_message,
                    created_at, updated_at
                )
                SELECT
                    'default', activity_id, name, activity_date, distance, duration,
                    sync_status, fit_path, garmin_result, synced_at, error_message,
                    created_at, updated_at
                FROM activities
                """
            )
            conn.execute("DROP TABLE activities")
            conn.execute("ALTER TABLE activities_v2 RENAME TO activities")
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_activities_user_date
                    ON activities(user_id, activity_date DESC)
                """
            )

    @staticmethod
    def _row_to_user(r: sqlite3.Row) -> UserRow:
        return UserRow(
            id=r["id"],
            slug=r["slug"],
            display_name=r["display_name"],
            email=r["email"],
            telegram=r["telegram"],
            timezone=r["timezone"],
            locale=normalize_locale(r["locale"] if "locale" in r.keys() else DEFAULT_LOCALE),
            hammerhead_user_id=r["hammerhead_user_id"],
            disabled=bool(r["disabled"]),
            is_admin=bool(r["is_admin"]),
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )

    def ensure_default_user(
        self,
        *,
        email: str = "owner@local",
        display_name: str = "Default",
        password: str = "changeme",
        hammerhead_user_id: str | None = None,
    ) -> UserRow:
        existing = self.get_user("default")
        if existing:
            if hammerhead_user_id and not existing.hammerhead_user_id:
                self.update_user(
                    "default",
                    hammerhead_user_id=hammerhead_user_id,
                )
                return self.get_user("default") or existing
            return existing
        return self.create_user(
            slug="default",
            display_name=display_name,
            email=email,
            password=password,
            timezone="Europe/Moscow",
            hammerhead_user_id=hammerhead_user_id,
            user_id="default",
            is_admin=True,
        )

    def create_user(
        self,
        *,
        slug: str,
        display_name: str,
        email: str,
        password: str,
        timezone: str = "Europe/Moscow",
        locale: str = DEFAULT_LOCALE,
        telegram: str | None = None,
        hammerhead_user_id: str | None = None,
        user_id: str | None = None,
        is_admin: bool = False,
    ) -> UserRow:
        slug = slug.strip().lower()
        if not _SLUG_RE.match(slug):
            raise ValueError("slug: 2–63 chars, a-z, 0-9, _, -")
        tz = normalize_timezone(timezone)
        loc = normalize_locale(locale)
        uid = (user_id or slug).strip()
        now = _utcnow()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO users (
                    id, slug, display_name, email, telegram, timezone, locale,
                    hammerhead_user_id, password_hash, disabled, is_admin,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    uid,
                    slug,
                    display_name.strip(),
                    email.strip().lower(),
                    telegram.strip() if telegram else None,
                    tz,
                    loc,
                    hammerhead_user_id,
                    hash_password(password),
                    1 if is_admin else 0,
                    now,
                    now,
                ),
            )
        row = self.get_user(uid)
        if not row:
            raise RuntimeError("user create failed")
        self._signal_admin_health()
        return row

    def update_user(
        self,
        user_id: str,
        *,
        display_name: str | None = None,
        email: str | None = None,
        telegram: str | None = None,
        timezone: str | None = None,
        locale: str | None = None,
        hammerhead_user_id: str | None = None,
        password: str | None = None,
        disabled: bool | None = None,
        is_admin: bool | None = None,
    ) -> None:
        fields: list[str] = ["updated_at = ?"]
        values: list[Any] = [_utcnow()]
        tz_val = normalize_timezone(timezone) if timezone is not None else None
        loc_val = normalize_locale(locale) if locale is not None else None
        for col, val in (
            ("display_name", display_name),
            ("email", email.strip().lower() if email else None),
            ("telegram", telegram),
            ("timezone", tz_val),
            ("locale", loc_val),
            ("hammerhead_user_id", hammerhead_user_id),
            ("disabled", 1 if disabled else 0 if disabled is False else None),
            ("is_admin", 1 if is_admin else 0 if is_admin is False else None),
        ):
            if val is not None:
                fields.append(f"{col} = ?")
                values.append(val)
        if password:
            fields.append("password_hash = ?")
            values.append(hash_password(password))
        values.append(user_id)
        with self._conn() as conn:
            conn.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
                values,
            )

    def get_user(self, user_id: str) -> UserRow | None:
        with self._conn() as conn:
            r = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return self._row_to_user(r) if r else None

    def get_user_by_email(self, email: str) -> UserRow | None:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email.strip().lower(),),
            ).fetchone()
        return self._row_to_user(r) if r else None

    def get_user_by_hammerhead_id(self, hammerhead_user_id: str) -> UserRow | None:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT * FROM users WHERE hammerhead_user_id = ?",
                (str(hammerhead_user_id),),
            ).fetchone()
        return self._row_to_user(r) if r else None

    def list_users(self) -> list[UserRow]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM users ORDER BY display_name COLLATE NOCASE"
            ).fetchall()
        return [self._row_to_user(r) for r in rows]

    def verify_user_password(self, email: str, password: str) -> UserRow | None:
        with self._conn() as conn:
            r = conn.execute(
                "SELECT * FROM users WHERE email = ?",
                (email.strip().lower(),),
            ).fetchone()
        if not r:
            return None
        from getsync.users.passwords import verify_password

        if not verify_password(password, r["password_hash"]):
            return None
        user = self._row_to_user(r)
        if user.disabled:
            return None
        return user

    def is_synced(
        self,
        user_id: str,
        activity_id: str,
        *,
        source: str = "hammerhead",
    ) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT sync_status FROM activities
                WHERE user_id = ? AND source = ? AND activity_id = ?
                """,
                (user_id, source, activity_id),
            ).fetchone()
        return row is not None and row["sync_status"] == "synced"

    def upsert_activity(
        self,
        user_id: str,
        activity_id: str,
        *,
        source: str = "hammerhead",
        name: str | None = None,
        activity_date: str | None = None,
        distance: float | None = None,
        duration: float | None = None,
        activity_type: str | None = None,
        sync_status: str | None = None,
        storage_key: str | None = None,
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
                """
                SELECT activity_id FROM activities
                WHERE user_id = ? AND source = ? AND activity_id = ?
                """,
                (user_id, source, activity_id),
            ).fetchone()
            health_signal = False
            if existing:
                fields: list[str] = ["updated_at = ?"]
                values: list[Any] = [now]
                for col, val in (
                    ("name", name),
                    ("activity_date", activity_date),
                    ("distance", distance),
                    ("duration", duration),
                    ("activity_type", activity_type),
                    ("sync_status", sync_status),
                    ("storage_key", storage_key),
                    ("garmin_result", garmin_json),
                    ("synced_at", synced_at),
                    ("error_message", error_message),
                ):
                    if val is not None:
                        fields.append(f"{col} = ?")
                        values.append(val)
                values.extend([user_id, source, activity_id])
                conn.execute(
                    f"UPDATE activities SET {', '.join(fields)} "
                    "WHERE user_id = ? AND source = ? AND activity_id = ?",
                    values,
                )
                if storage_key is not None:
                    health_signal = True
            else:
                conn.execute(
                    """
                    INSERT INTO activities (
                        user_id, source, activity_id, name, activity_date, distance, duration,
                        activity_type, sync_status, storage_key, garmin_result,
                        synced_at, error_message, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        source,
                        activity_id,
                        name,
                        activity_date,
                        distance,
                        duration,
                        activity_type,
                        sync_status or "pending",
                        storage_key,
                        garmin_json,
                        synced_at,
                        error_message,
                        now,
                        now,
                    ),
                )
                health_signal = True
        if health_signal:
            self._signal_admin_health()

    def mark_synced(
        self,
        user_id: str,
        activity_id: str,
        garmin_result: dict[str, Any],
        *,
        storage_key: str,
        name: str | None = None,
        activity_date: str | None = None,
        distance: float | None = None,
        duration: float | None = None,
    ) -> None:
        self.upsert_activity(
            user_id,
            activity_id,
            name=name,
            activity_date=activity_date,
            distance=distance,
            duration=duration,
            sync_status="synced",
            storage_key=storage_key,
            garmin_result=garmin_result,
            synced_at=_utcnow(),
            error_message=None,
        )

    def mark_error(self, user_id: str, activity_id: str, message: str) -> None:
        self.upsert_activity(
            user_id,
            activity_id,
            sync_status="error",
            error_message=message[:2000],
        )

    def log_event(
        self,
        event_type: str,
        message: str = "",
        activity_id: str | None = None,
        *,
        user_id: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO sync_events (user_id, activity_id, event_type, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, activity_id, event_type, message[:2000] or None, _utcnow()),
            )
        _audit_log.info(
            "sync user=%s activity=%s event=%s msg=%s",
            user_id or "—",
            activity_id or "—",
            event_type,
            (message or "")[:500],
        )
        self._signal_admin_log()

    def log_admin_audit(
        self,
        event_type: str,
        message: str = "",
        *,
        user_id: str | None = None,
        subject: str | None = None,
        actor_user_id: str | None = None,
    ) -> None:
        """Admin-visible audit: user create/update, registration, etc."""
        msg = (message or "")[:2000] or None
        if actor_user_id:
            actor = self.get_user(actor_user_id)
            who = actor.slug if actor else actor_user_id
            msg = f"by {who}: {msg}" if msg else f"by {who}"
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO admin_audit_events (
                    user_id, actor_user_id, event_type, subject, message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, actor_user_id, event_type, subject, msg, _utcnow()),
            )
        _audit_log.info(
            "admin user=%s actor=%s event=%s subject=%s msg=%s",
            user_id or "—",
            actor_user_id or "—",
            event_type,
            subject or "—",
            (msg or "")[:500],
        )
        self._signal_admin_log()
        self._signal_admin_health()

    def count_activities_by_status(
        self,
        user_id: str,
        *,
        source: str | None = None,
    ) -> dict[str, int]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT sync_status, COUNT(*) AS n FROM activities
                WHERE user_id = ? AND (? IS NULL OR source = ?)
                GROUP BY sync_status
                """,
                (user_id, source, source),
            ).fetchall()
        return {str(r["sync_status"]): int(r["n"]) for r in rows}

    def list_activities(
        self,
        user_id: str,
        limit: int = 50,
        *,
        source: str | None = None,
        sync_status: str | None = None,
    ) -> list[ActivityRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT user_id, source, activity_id, name, activity_date, distance, duration,
                       activity_type, sync_status, storage_key, synced_at,
                       error_message
                FROM activities
                WHERE user_id = ?
                  AND (? IS NULL OR source = ?)
                  AND (? IS NULL OR sync_status = ?)
                ORDER BY COALESCE(activity_date, created_at) DESC
                LIMIT ?
                """,
                (user_id, source, source, sync_status, sync_status, limit),
            ).fetchall()
        return [self._activity_from_row(r) for r in rows]

    def list_activity_calendar_rows(
        self,
        user_id: str,
        *,
        source: str | None = None,
    ) -> list[tuple[str, str]]:
        """(activity_date, sync_status) for month calendar aggregation."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT activity_date, sync_status FROM activities
                WHERE user_id = ?
                  AND activity_date IS NOT NULL AND TRIM(activity_date) != ''
                  AND (? IS NULL OR source = ?)
                """,
                (user_id, source, source),
            ).fetchall()
        return [(str(r["activity_date"]), str(r["sync_status"])) for r in rows]

    def list_activity_catalog(
        self,
        user_id: str,
        *,
        source: str | None = None,
    ) -> list[ActivityRow]:
        """All catalog rows for browse (any date)."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT user_id, source, activity_id, name, activity_date, distance, duration,
                       activity_type, sync_status, storage_key, synced_at,
                       error_message
                FROM activities
                WHERE user_id = ?
                  AND (? IS NULL OR source = ?)
                ORDER BY activity_date DESC
                """,
                (user_id, source, source),
            ).fetchall()
        return [self._activity_from_row(r) for r in rows]

    def list_activity_catalog_for_calendar(
        self,
        user_id: str,
        *,
        source: str | None = None,
    ) -> list[ActivityRow]:
        """Full catalog rows with dates (month grid + per-day activity chips)."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT user_id, source, activity_id, name, activity_date, distance, duration,
                       activity_type, sync_status, storage_key, synced_at,
                       error_message
                FROM activities
                WHERE user_id = ?
                  AND activity_date IS NOT NULL AND TRIM(activity_date) != ''
                  AND (? IS NULL OR source = ?)
                ORDER BY activity_date DESC
                """,
                (user_id, source, source),
            ).fetchall()
        return [self._activity_from_row(r) for r in rows]

    def count_catalog(self, user_id: str, *, source: str | None = None) -> int:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM activities
                WHERE user_id = ? AND (? IS NULL OR source = ?)
                """,
                (user_id, source, source),
            ).fetchone()
        return int(row["n"]) if row else 0

    def update_activity_name(
        self,
        user_id: str,
        activity_id: str,
        name: str,
        *,
        source: str,
    ) -> bool:
        label = name.strip()
        if not label:
            return False
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE activities
                SET name = ?, updated_at = ?
                WHERE user_id = ? AND source = ? AND activity_id = ?
                """,
                (label, _utcnow(), user_id, source, activity_id),
            )
        return cur.rowcount > 0

    def delete_activity(
        self,
        user_id: str,
        activity_id: str,
        *,
        source: str,
    ) -> tuple[bool, str | None]:
        """Remove catalog row. Returns (found, storage_key) for optional FIT cleanup."""
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT storage_key FROM activities
                WHERE user_id = ? AND source = ? AND activity_id = ?
                """,
                (user_id, source, activity_id),
            ).fetchone()
            if row is None:
                return False, None
            storage_key = row["storage_key"]
            conn.execute(
                """
                DELETE FROM activities
                WHERE user_id = ? AND source = ? AND activity_id = ?
                """,
                (user_id, source, activity_id),
            )
        self._signal_admin_health()
        return True, storage_key

    def get_activity(
        self,
        user_id: str,
        activity_id: str,
        *,
        source: str = "hammerhead",
    ) -> ActivityRow | None:
        with self._conn() as conn:
            r = conn.execute(
                """
                SELECT user_id, source, activity_id, name, activity_date, distance, duration,
                       activity_type, sync_status, storage_key, synced_at,
                       error_message
                FROM activities
                WHERE user_id = ? AND source = ? AND activity_id = ?
                """,
                (user_id, source, activity_id),
            ).fetchone()
        return self._activity_from_row(r) if r else None

    @staticmethod
    def _activity_from_row(r: sqlite3.Row) -> ActivityRow:
        keys = r.keys()
        return ActivityRow(
            user_id=r["user_id"],
            source=r["source"] if "source" in keys else "hammerhead",
            activity_id=r["activity_id"],
            name=r["name"],
            activity_date=r["activity_date"],
            distance=r["distance"],
            duration=r["duration"],
            activity_type=r["activity_type"] if "activity_type" in keys else None,
            sync_status=r["sync_status"],
            storage_key=r["storage_key"] if "storage_key" in keys else None,
            synced_at=r["synced_at"],
            error_message=r["error_message"],
        )

    def list_events(
        self,
        limit: int = 100,
        offset: int = 0,
        *,
        user_id: str | None = None,
    ) -> list[SyncEventRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, activity_id, event_type, message, created_at
                FROM sync_events
                WHERE (? IS NULL OR user_id = ?)
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, user_id, limit, offset),
            ).fetchall()
        return [
            SyncEventRow(
                id=r["id"],
                user_id=r["user_id"],
                activity_id=r["activity_id"],
                event_type=r["event_type"],
                message=r["message"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    def count_events(self, user_id: str | None = None) -> int:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS n FROM sync_events
                WHERE (? IS NULL OR user_id = ?)
                """,
                (user_id, user_id),
            ).fetchone()
        return int(row["n"]) if row else 0

    def count_admin_log(self, user_id: str | None = None) -> int:
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM sync_events
                   WHERE (? IS NULL OR user_id = ?))
                + (SELECT COUNT(*) FROM session_refresh_events
                   WHERE (? IS NULL OR user_id = ?))
                + (SELECT COUNT(*) FROM admin_audit_events
                   WHERE (? IS NULL OR user_id = ?))
                AS n
                """,
                (user_id, user_id, user_id, user_id, user_id, user_id),
            ).fetchone()
        return int(row["n"]) if row else 0

    def list_admin_log(
        self,
        limit: int = 50,
        offset: int = 0,
        *,
        user_id: str | None = None,
    ) -> list[AdminLogRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT created_at, user_id, log_kind, event_type, subject, message
                FROM (
                    SELECT created_at, user_id, 'sync' AS log_kind, event_type,
                           activity_id AS subject, message
                    FROM sync_events
                    WHERE (? IS NULL OR user_id = ?)
                    UNION ALL
                    SELECT created_at, user_id, 'garmin' AS log_kind, event_type,
                           trigger AS subject, message
                    FROM session_refresh_events
                    WHERE (? IS NULL OR user_id = ?)
                    UNION ALL
                    SELECT created_at, user_id, 'admin' AS log_kind, event_type,
                           COALESCE(subject, actor_user_id) AS subject, message
                    FROM admin_audit_events
                    WHERE (? IS NULL OR user_id = ?)
                )
                ORDER BY created_at DESC, log_kind DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, user_id, user_id, user_id, user_id, user_id, limit, offset),
            ).fetchall()
        return [
            AdminLogRow(
                created_at=r["created_at"],
                user_id=r["user_id"],
                log_kind=r["log_kind"],
                event_type=r["event_type"],
                subject=r["subject"],
                message=r["message"],
            )
            for r in rows
        ]

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

    def build_sync_index(self, user_id: str) -> dict[str, SyncIndexEntry]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT activity_id, sync_status, garmin_result, storage_key,
                       synced_at, error_message
                FROM activities
                WHERE user_id = ? AND source = 'hammerhead'
                """,
                (user_id,),
            ).fetchall()
        index: dict[str, SyncIndexEntry] = {}
        for r in rows:
            garmin_result = r["garmin_result"]
            keys = r.keys()
            index[r["activity_id"]] = SyncIndexEntry(
                activity_id=r["activity_id"],
                sync_status=r["sync_status"],
                garmin_id=self._garmin_id_from_result(garmin_result),
                garmin_upload_status=self._upload_status_from_result(garmin_result),
                storage_key=r["storage_key"] if "storage_key" in keys else None,
                synced_at=r["synced_at"],
                error_message=r["error_message"],
            )
        return index

    def log_session_refresh(
        self,
        trigger: str,
        event_type: str,
        message: str = "",
        *,
        user_id: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO session_refresh_events (user_id, trigger, event_type, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, trigger, event_type, message[:2000] or None, _utcnow()),
            )
        _audit_log.info(
            "session user=%s trigger=%s event=%s msg=%s",
            user_id or "—",
            trigger,
            event_type,
            (message or "")[:500],
        )
        self._signal_admin_log()

    def list_session_refresh_events(
        self,
        limit: int = 100,
        *,
        user_id: str | None = None,
    ) -> list[SessionRefreshEventRow]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, trigger, event_type, message, created_at
                FROM session_refresh_events
                WHERE (? IS NULL OR user_id = ?)
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, user_id, limit),
            ).fetchall()
        return [
            SessionRefreshEventRow(
                id=r["id"],
                user_id=r["user_id"],
                trigger=r["trigger"],
                event_type=r["event_type"],
                message=r["message"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    @staticmethod
    def _signal_admin_log() -> None:
        try:
            from getsync.web.realtime_signals import schedule_admin_log_refresh

            schedule_admin_log_refresh()
        except Exception:
            pass

    @staticmethod
    def _signal_admin_health() -> None:
        try:
            from getsync.web.realtime_signals import schedule_admin_health_refresh

            schedule_admin_health_refresh()
        except Exception:
            pass
