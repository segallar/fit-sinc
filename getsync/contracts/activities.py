"""Activity contracts: normalized DTO and source/sink Protocols."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol, runtime_checkable

from getsync.contracts.connections import ConnectionStatus
from getsync.users.context import UserContext


@dataclass(frozen=True)
class NormalizedActivity:
    """Cross-module activity DTO. Provider payloads must not cross module boundaries."""

    user_id: str
    source: str
    activity_id: str
    name: str | None = None
    activity_date: str | None = None
    distance: float | None = None
    duration: float | None = None
    activity_type: str | None = None
    sync_status: str | None = None
    storage_key: str | None = None


@dataclass(frozen=True)
class ActivityPage:
    items: tuple[NormalizedActivity, ...]
    page: int
    total_pages: int
    total_items: int | None = None
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class UploadResult:
    """Sink upload outcome (provider-agnostic fields)."""

    status: str
    message: str = ""
    raw: dict[str, Any] | None = None


@runtime_checkable
class ActivitySource(Protocol):
    """Read activities from an external provider."""

    source_id: str

    async def fetch_page(
        self,
        ctx: UserContext,
        *,
        page: int = 1,
        per_page: int = 50,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ActivityPage: ...

    def connection_status(self, ctx: UserContext) -> ConnectionStatus: ...


@runtime_checkable
class ActivitySourceWithArtifacts(ActivitySource, Protocol):
    """Source that can download FIT binaries (e.g. Hammerhead)."""

    async def fetch_metadata(
        self, ctx: UserContext, activity_id: str
    ) -> NormalizedActivity | None: ...

    async def download_fit(self, ctx: UserContext, activity_id: str) -> bytes: ...


@runtime_checkable
class ActivitySink(Protocol):
    """Upload activities to an external provider."""

    sink_id: str

    async def upload_fit(
        self,
        ctx: UserContext,
        activity_id: str,
        fit: bytes,
        filename: str,
    ) -> UploadResult: ...

    def connection_status(self, ctx: UserContext) -> ConnectionStatus: ...
