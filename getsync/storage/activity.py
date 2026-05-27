"""Per-user activity artifact storage (FIT, GPX, …)."""

from __future__ import annotations

from pathlib import Path

from getsync.storage.backend import StorageBackend, get_storage_backend
from getsync.storage.keys import build_object_key
from getsync.users.context import UserContext


class ActivityStorage:
    """Facade: logical keys + StorageBackend for one tenant."""

    def __init__(
        self,
        ctx: UserContext,
        backend: StorageBackend | None = None,
    ) -> None:
        self._ctx = ctx
        self._backend = backend or get_storage_backend(ctx.settings)

    @property
    def user_id(self) -> str:
        return self._ctx.user_id

    @property
    def activities_root(self) -> Path:
        """Local: data/users/{id}/activities/ (prefix for all sources)."""
        return self._ctx.user_data_dir / "activities"

    def fit_key(self, source: str, external_id: str) -> str:
        return build_object_key(source, external_id, kind="fit")

    def put_fit(self, source: str, external_id: str, data: bytes) -> str:
        key = self.fit_key(source, external_id)
        self._backend.put(
            self.user_id,
            key,
            data,
            content_type="application/vnd.ant.fit",
        )
        return key

    def has_fit(self, storage_key: str | None) -> bool:
        if not storage_key:
            return False
        return self._backend.exists(self.user_id, storage_key)

    def open_fit_path(self, storage_key: str | None) -> Path | None:
        if not storage_key:
            return None
        return self._backend.open_path(self.user_id, storage_key)
