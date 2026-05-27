"""App health and storage metrics for admin UI."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from getsync import __version__
from getsync.build_info import deploy_number, deployed_at_iso, git_commit_short
from getsync.config import Settings
from getsync.users.bootstrap import registration_is_open


@dataclass(frozen=True)
class PathBytes:
    label: str
    path: str
    bytes: int
    exists: bool

    @property
    def size_human(self) -> str:
        return format_bytes(self.bytes)


@dataclass(frozen=True)
class FitStorageUserRow:
    user_id: str
    slug: str
    bytes: int
    fit_count: int

    @property
    def size_human(self) -> str:
        return format_bytes(self.bytes)


@dataclass(frozen=True)
class FitStorageSummary:
    total_bytes: int
    fit_count: int
    users: tuple[FitStorageUserRow, ...]

    @property
    def total_human(self) -> str:
        return format_bytes(self.total_bytes)


def format_bytes(size: int) -> str:
    if size < 0:
        size = 0
    if size < 1024:
        return f"{size} B"
    value = float(size)
    for unit in ("KB", "MB", "GB", "TB"):
        value /= 1024.0
        if value < 1024.0 or unit == "TB":
            if unit == "KB":
                return f"{value:.1f} {unit}"
            return f"{value:.2f} {unit}"
    return f"{value:.2f} PB"


def _file_size(path: Path) -> int:
    try:
        return path.stat().st_size if path.is_file() else 0
    except OSError:
        return 0


def _dir_size_and_fit_count(root: Path) -> tuple[int, int]:
    if not root.is_dir():
        return 0, 0
    total = 0
    fit_count = 0
    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                total += path.stat().st_size
            except OSError:
                continue
            if path.suffix.lower() == ".fit":
                fit_count += 1
    except OSError:
        pass
    return total, fit_count


def sqlite_file_sizes(db_path: Path) -> list[PathBytes]:
    rows: list[PathBytes] = []
    for suffix, label in (
        ("", "getsync.db"),
        ("-wal", "getsync.db-wal"),
        ("-shm", "getsync.db-shm"),
    ):
        path = Path(f"{db_path}{suffix}")
        rows.append(
            PathBytes(
                label=label,
                path=str(path),
                bytes=_file_size(path),
                exists=path.is_file(),
            )
        )
    return rows


def scan_fit_storage(data_dir: Path, *, users: list[tuple[str, str]]) -> FitStorageSummary:
    """Sum activity artifacts per tenant; count .fit files under activities/."""
    per_user: list[FitStorageUserRow] = []
    total_bytes = 0
    total_fits = 0
    users_dir = data_dir / "users"
    known = {uid: slug for uid, slug in users}

    if users_dir.is_dir():
        for user_dir in sorted(users_dir.iterdir()):
            if not user_dir.is_dir():
                continue
            uid = user_dir.name
            activities = user_dir / "activities"
            nbytes, nfit = _dir_size_and_fit_count(activities)
            if nbytes == 0 and nfit == 0 and uid not in known:
                continue
            per_user.append(
                FitStorageUserRow(
                    user_id=uid,
                    slug=known.get(uid, "—"),
                    bytes=nbytes,
                    fit_count=nfit,
                )
            )
            total_bytes += nbytes
            total_fits += nfit

    per_user.sort(key=lambda r: (-r.bytes, r.user_id))
    return FitStorageSummary(
        total_bytes=total_bytes,
        fit_count=total_fits,
        users=tuple(per_user),
    )


def sqlite_table_counts(db_path: Path) -> dict[str, int]:
    if not db_path.is_file():
        return {}
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
            counts: dict[str, int] = {}
            queries = {
                "users": "SELECT COUNT(*) FROM users",
                "activities": "SELECT COUNT(*) FROM activities",
                "sync_events": "SELECT COUNT(*) FROM sync_events",
                "session_refresh_events": "SELECT COUNT(*) FROM session_refresh_events",
            }
            for table, sql in queries.items():
                try:
                    row = conn.execute(sql).fetchone()
                    counts[table] = int(row[0]) if row else 0
                except sqlite3.Error:
                    counts[table] = 0
            return counts
    except sqlite3.Error:
        return {}


def log_file_stats(data_dir: Path) -> PathBytes | None:
    log_path = data_dir / "logs" / "getsync.log"
    if not log_path.is_file():
        return None
    total = _file_size(log_path)
    for rotated in log_path.parent.glob("getsync.log.*"):
        total += _file_size(rotated)
    return PathBytes(
        label="getsync.log (+ rotations)",
        path=str(log_path),
        bytes=total,
        exists=True,
    )


def build_admin_health_context(settings: Settings, store) -> dict[str, object]:
    """Template context for admin App Health page."""
    users = store.list_users()
    user_pairs = [(u.id, u.slug) for u in users]
    db_files = sqlite_file_sizes(settings.db_path)
    db_bytes = sum(f.bytes for f in db_files if f.exists)
    table_counts = sqlite_table_counts(settings.db_path)
    fit_storage = scan_fit_storage(settings.data_dir, users=user_pairs)
    data_dir_size, _ = _dir_size_and_fit_count(settings.data_dir)

    return {
        "health_status": "ok",
        "health_version": __version__,
        "health_commit": git_commit_short(),
        "health_deploy_number": deploy_number(),
        "health_deployed_at": deployed_at_iso(),
        "health_registration_open": registration_is_open(settings),
        "health_storage_backend": settings.storage_backend,
        "health_data_dir": str(settings.data_dir.resolve()),
        "health_db_path": str(settings.db_path.resolve()),
        "health_db_files": db_files,
        "health_db_bytes": db_bytes,
        "health_db_bytes_human": format_bytes(db_bytes),
        "health_data_dir_bytes": data_dir_size,
        "health_data_dir_bytes_human": format_bytes(data_dir_size),
        "health_table_counts": table_counts,
        "health_user_count": len(users),
        "health_fit_storage": fit_storage,
        "health_log_file": log_file_stats(settings.data_dir),
        "health_public_url": "/health",
    }
