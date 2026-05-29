"""Public catalog API: storage port + provider ingest."""

from __future__ import annotations

from datetime import date
from typing import Literal

from getsync.catalog.application.refresh import (
    UI_REFRESH_MAX_PAGES,
    RefreshResult,
)
from getsync.catalog.application.refresh import (
    refresh_from_providers as _refresh,
)
from getsync.catalog.infra.store_catalog import StoreCatalog
from getsync.contracts.persistence import ActivityCatalog
from getsync.state.store import Store
from getsync.users.context import UserContext, as_context

Source = Literal["hammerhead", "garmin", "strava"]

__all__ = [
    "RefreshResult",
    "Source",
    "UI_REFRESH_MAX_PAGES",
    "get_catalog",
    "refresh_from_providers",
]


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
    date_from: date | None = None,
    date_to: date | None = None,
    max_pages: int | None = None,
) -> RefreshResult:
    """Pull provider metadata into the catalog (explicit refresh / background ingest)."""
    user_ctx = as_context(ctx)
    cat = catalog or get_catalog(user_ctx)
    from getsync.catalog.application.scan import MAX_SCAN_PAGES

    pages = MAX_SCAN_PAGES if max_pages is None else max_pages
    return await _refresh(
        cat,
        user_ctx,
        sources=sources,
        force=force,
        date_from=date_from,
        date_to=date_to,
        max_pages=pages,
    )
