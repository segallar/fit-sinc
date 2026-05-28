"""Browse filters and view modes."""

from __future__ import annotations

import calendar as cal_mod
from dataclasses import dataclass
from datetime import date
from typing import Literal

Source = Literal["hammerhead", "garmin"]
SourceFilter = Literal["", "hammerhead", "garmin"]
BrowseMode = Literal["all", "hammerhead", "garmin"]

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
        if s in ("hammerhead", "garmin"):
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
