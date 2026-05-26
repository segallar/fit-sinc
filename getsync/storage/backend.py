"""Storage backends for activity artifacts (local disk, S3 later)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from getsync.config import Settings


class StorageBackend(Protocol):
    """Per-user object storage; keys are relative to user_id prefix."""

    def put(
        self,
        user_id: str,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None: ...

    def exists(self, user_id: str, key: str) -> bool: ...

    def open_path(self, user_id: str, key: str) -> Path | None:
        """Local filesystem path when available (for upload / FileResponse)."""
        ...

    def delete(self, user_id: str, key: str) -> None: ...


class LocalFilesystemBackend:
    """
    Layout: {data_dir}/users/{user_id}/{key}

    Example key: activities/hammerhead/abc.fit
    → data/users/u1/activities/hammerhead/abc.fit
    """

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir

    def _path(self, user_id: str, key: str) -> Path:
        normalized = key.replace("\\", "/").lstrip("/")
        if ".." in normalized.split("/"):
            raise ValueError("invalid storage key")
        return self._data_dir / "users" / user_id / normalized

    def put(
        self,
        user_id: str,
        key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> None:
        path = self._path(user_id, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def exists(self, user_id: str, key: str) -> bool:
        return self._path(user_id, key).is_file()

    def open_path(self, user_id: str, key: str) -> Path | None:
        path = self._path(user_id, key)
        return path if path.is_file() else None

    def delete(self, user_id: str, key: str) -> None:
        path = self._path(user_id, key)
        if path.is_file():
            path.unlink()


class S3StorageBackend:
    """Placeholder for phase 11.1 — same key layout as LocalFilesystemBackend."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _not_ready(self) -> None:
        raise NotImplementedError(
            "S3 storage is not implemented yet; set STORAGE_BACKEND=local"
        )

    def put(self, user_id: str, key: str, data: bytes, *, content_type: str = "") -> None:
        self._not_ready()

    def exists(self, user_id: str, key: str) -> bool:
        self._not_ready()

    def open_path(self, user_id: str, key: str) -> Path | None:
        self._not_ready()

    def delete(self, user_id: str, key: str) -> None:
        self._not_ready()


def get_storage_backend(settings: Settings) -> StorageBackend:
    backend = (settings.storage_backend or "local").strip().lower()
    if backend == "local":
        return LocalFilesystemBackend(settings.data_dir)
    if backend == "s3":
        return S3StorageBackend(settings)
    raise ValueError(f"unknown STORAGE_BACKEND: {backend!r}")
