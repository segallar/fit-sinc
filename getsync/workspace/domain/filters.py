"""Browse filters and view modes."""

from __future__ import annotations

import calendar as cal_mod
from dataclasses import dataclass
from datetime import date
from typing import Literal

Source = Literal["hammerhead", "garmin", "strava"]
SourceFilter = Literal["", "hammerhead", "garmin", "strava"]
BrowseMode = Literal["all", "hammerhead", "garmin", "strava"]

ACTIVITY_TYPE_FILTER_CHOICES: tuple[tuple[str, str], ...] = (
    ("", "All types"),
    ("cycling", "Cycling"),
    ("running", "Running"),
    ("swimming", "Swimming"),
    ("walking", "Walking"),
    ("hiking", "Hiking"),
    ("mountain_biking", "Mountain biking"),
    ("triathlon", "Triathlon"),
)

# Substrings matched against lowercased provider activity_type (e.g. Strava sport_type).
_ACTIVITY_TYPE_ALIASES: dict[str, tuple[str, ...]] = {
    "cycling": ("ride", "bike", "bik", "cycl", "velo"),
    "running": ("run", "jog", "trail"),
    "swimming": ("swim",),
    "walking": ("walk",),
    "hiking": ("hike",),
    "mountain_biking": ("mountain", "mtb", "gravel"),
    "triathlon": ("tri",),
}


def activity_type_matches(filter_value: str, row_type: str | None) -> bool:
    needle = filter_value.strip().lower()
    if not needle:
        return True
    hay = (row_type or "").lower()
    if needle in hay:
        return True
    return any(alias in hay for alias in _ACTIVITY_TYPE_ALIASES.get(needle, ()))


@dataclass(frozen=True)
class ActivityFilters:
    q: str = ""
    status: str = ""
    activity_type: str = ""
    date_from: str = ""
    date_to: str = ""
    source: str = ""

    def has_content_filters(self) -> bool:
        return bool(
            self.q.strip()
            or self.status.strip()
            or self.activity_type.strip()
            or self.date_from.strip()
            or self.date_to.strip()
        )

    def is_active(self) -> bool:
        return self.has_content_filters() or bool(self.source.strip())

    def source_filter(self) -> SourceFilter:
        s = self.source.strip().lower()
        if s in ("hammerhead", "garmin", "strava"):
            return s  # type: ignore[return-value]
        return ""


def month_date_bounds_iso(year: int, month: int) -> tuple[str, str]:
    last = cal_mod.monthrange(year, month)[1]
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"


def resolve_activity_filters(
    filters: ActivityFilters,
    *,
    view: str,
    year: int,
    month: int,
    today: date,
) -> ActivityFilters:
    """Match subheader month range: filter by visible from/to when URL dates omitted."""
    if filters.date_from.strip() or filters.date_to.strip():
        return filters
    ref_year, ref_month = (year, month) if view == "calendar" else (today.year, today.month)
    start, end = month_date_bounds_iso(ref_year, ref_month)
    return ActivityFilters(
        q=filters.q,
        status=filters.status,
        activity_type=filters.activity_type,
        date_from=start,
        date_to=end,
        source=filters.source,
    )
