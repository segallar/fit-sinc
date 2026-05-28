"""Public catalog API: storage port + provider ingest."""

from __future__ import annotations

from typing import Literal

from getsync.catalog.application.refresh import RefreshResult, refresh_from_providers as _refresh
from getsync.catalog.infra.store_catalog import StoreCatalog
from getsync.contracts.persistence import ActivityCatalog
from getsync.state.store import Store
from getsync.users.context import UserContext, as_context

Source = Literal["hammerhead", "garmin"]

__all__ = ["RefreshResult", "Source", "get_catalog", "refresh_from_providers"]


def get_catalog(ctx: UserContext | None = None, *, db_path: str | None = None) -> ActivityCatalog:
    """Return ActivityCatalog for the given user context."""
    user_ctx = as_context(ctx)
    path = db_path or user_ctx.db_path
    return StoreCatalog(Store(path))


async def refresh_from_providers(
    ctx: UserContext | None = None,
    *,
    sources: tuple[Source, ...] | None = None,
    force: bool = False,
    catalog: ActivityCatalog | None = None,
) -> RefreshResult:
    """Pull provider metadata into the catalog (explicit refresh / background ingest)."""
    user_ctx = as_context(ctx)
    cat = catalog or get_catalog(user_ctx)
    return await _refresh(cat, user_ctx, sources=sources, force=force)
