"""Pull activity metadata from providers into the catalog."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from getsync.catalog.application.ingest import persist_normalized_rows
from getsync.catalog.application.scan import scan_source
from getsync.contracts.persistence import ActivityCatalog
from getsync.providers.strava.client import StravaClient
from getsync.users.context import UserContext

Source = Literal["hammerhead", "garmin", "strava"]


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
) -> RefreshResult:
    """Ingest metadata from registered sources into the catalog."""
    selected: tuple[Source, ...] = sources or default_refresh_sources(ctx)
    errors: list[str] = []
    counts: dict[str, int] = {"hammerhead": 0, "garmin": 0, "strava": 0}

    for source_id in selected:
        try:
            rows = await scan_source(source_id, catalog, ctx)
            if rows:
                persist_normalized_rows(catalog, rows)
            if source_id in counts:
                counts[source_id] = len(rows)
        except Exception as exc:
            label = source_id.capitalize()
            errors.append(f"{label}: {exc}")

    return RefreshResult(
        hammerhead_count=counts["hammerhead"],
        garmin_count=counts["garmin"],
        strava_count=counts["strava"],
        errors=tuple(errors),
    )
