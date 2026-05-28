"""Browse row DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from getsync.workspace.domain.filters import ActivityFilters, BrowseMode, Source


@dataclass(frozen=True)
class ActivityBrowseRow:
    source: Source
    external_id: str
    name: str
    activity_date: str | None
    distance: float | None
    duration: float | None
    activity_type: str | None
    sync_status: str
    sync_detail: str | None
    hammerhead_id: str | None
    garmin_id: int | None
    fit_available: bool


@dataclass(frozen=True)
class ActivityBrowsePage:
    mode: BrowseMode
    rows: list[ActivityBrowseRow]
    page: int
    per_page: int
    total: int
    total_pages: int
    filters: ActivityFilters
    error: str | None = None
