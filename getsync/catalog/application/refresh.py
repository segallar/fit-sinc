"""Pull activity metadata from providers into the catalog."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Literal

from getsync.catalog.application.ingest import persist_normalized_rows
from getsync.catalog.application.scan import MAX_SCAN_PAGES, scan_source
from getsync.contracts.activities import NormalizedActivity
from getsync.contracts.persistence import ActivityCatalog
from getsync.providers.strava.client import StravaClient
from getsync.users.context import UserContext

Source = Literal["hammerhead", "garmin", "strava"]

UI_REFRESH_MAX_PAGES = 5


def default_refresh_sources(ctx: UserContext) -> tuple[Source, ...]:
    """Sources to pull on UI refresh — include Strava when user is connected."""
    sources: list[Source] = ["hammerhead", "garmin"]
    if StravaClient(ctx).load_tokens() is not None:
        sources.append("strava")
    return tuple(sources)


@dataclass(frozen=True)
class RefreshResult:
    hammerhead_count: int
    garmin_count: int
    strava_count: int = 0
    errors: tuple[str, ...] = ()


async def refresh_from_providers(
    catalog: ActivityCatalog,
    ctx: UserContext,
    *,
    sources: tuple[Source, ...] | None = None,
    force: bool = False,  # noqa: ARG001 — reserved for incremental refresh
    date_from: date | None = None,
    date_to: date | None = None,
    max_pages: int = MAX_SCAN_PAGES,
) -> RefreshResult:
    """Ingest metadata from registered sources into the catalog."""
    selected: tuple[Source, ...] = sources or default_refresh_sources(ctx)
    errors: list[str] = []
    counts: dict[str, int] = {"hammerhead": 0, "garmin": 0, "strava": 0}
    page_cap = max(1, min(max_pages, MAX_SCAN_PAGES))

    async def _pull(source_id: Source) -> tuple[Source, list[NormalizedActivity] | BaseException]:
        try:
            rows = await scan_source(
                source_id,
                catalog,
                ctx,
                max_pages=page_cap,
                date_from=date_from,
                date_to=date_to,
            )
            return source_id, rows
        except Exception as exc:
            return source_id, exc

    outcomes = await asyncio.gather(*(_pull(source_id) for source_id in selected))

    for source_id, outcome in outcomes:
        if isinstance(outcome, BaseException):
            errors.append(f"{source_id.capitalize()}: {outcome}")
            continue
        rows = outcome
        if rows:
            persist_normalized_rows(catalog, rows)
        counts[source_id] = len(rows)

    return RefreshResult(
        hammerhead_count=counts["hammerhead"],
        garmin_count=counts["garmin"],
        strava_count=counts["strava"],
        errors=tuple(errors),
    )
