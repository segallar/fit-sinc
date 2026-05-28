"""Activity month calendar from catalog snapshot."""

from __future__ import annotations

import calendar as cal_mod
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from getsync.catalog.api import get_catalog
from getsync.contracts.persistence import ActivityCatalog, SyncIndexEntry
from getsync.timeutil import _parse_iso, zone_info
from getsync.users.context import UserContext, as_context
from getsync.users.timezones import DEFAULT_TIMEZONE, normalize_timezone
from getsync.workspace.application.mapping import normalized_to_browse_row
from getsync.workspace.domain.filters import ActivityFilters
from getsync.workspace.domain.rows import ActivityBrowseRow
from getsync.workspace.application.browse import _matches_filters

_STATUS_RANK: dict[str, int] = {
    "error": 4,
    "pending": 3,
    "not synced": 2,
    "synced": 1,
}


@dataclass(frozen=True)
class CalendarDayStat:
    count: int
    worst_status: str | None


@dataclass(frozen=True)
class CalendarDayCell:
    iso: str
    day_num: int
    in_month: bool
    count: int
    worst_status: str | None
    is_today: bool
    is_selected: bool
    list_href: str
    activities: tuple[ActivityBrowseRow, ...] = ()
    activity_rows: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ActivityCalendarView:
    year: int
    month: int
    month_label: str
    weekday_labels: tuple[str, ...]
    weeks: tuple[tuple[CalendarDayCell, ...], ...]
    prev_href: str
    next_href: str
    today_href: str
    total_in_month: int
    source_note: str


def format_activity_chip_name(
    name: str | None,
    activity_date: str | None,
    *,
    display_tz: str | None = None,
) -> str:
    """Calendar chip label: local time + activity name (e.g. ``11:55 Morning Ride``)."""
    label = (name or "—").strip() or "—"
    tz_name = normalize_timezone(display_tz or DEFAULT_TIMEZONE)
    dt = _parse_iso(activity_date or "", tz=tz_name)
    if dt is None:
        return label
    return f"{dt:%H:%M} {label}"


def _worst_status(current: str | None, new: str) -> str:
    if not new:
        return current or ""
    if current is None:
        return new
    if _STATUS_RANK.get(new, 0) > _STATUS_RANK.get(current, 0):
        return new
    return current


def aggregate_days_by_local_date(
    rows: list[tuple[str, str]],
    *,
    display_tz: str,
    year: int,
    month: int,
) -> dict[str, CalendarDayStat]:
    stats: dict[str, CalendarDayStat] = {}
    for activity_date, sync_status in rows:
        dt = _parse_iso(activity_date, tz=display_tz)
        if dt is None:
            continue
        if dt.year != year or dt.month != month:
            continue
        iso = dt.date().isoformat()
        prev = stats.get(iso)
        count = (prev.count if prev else 0) + 1
        worst = _worst_status(prev.worst_status if prev else None, sync_status)
        stats[iso] = CalendarDayStat(count=count, worst_status=worst or None)
    return stats


def _browse_sort_key(row: ActivityBrowseRow) -> float:
    dt = _parse_iso(row.activity_date or "")
    return -(dt.timestamp() if dt else 0.0)


def _activities_by_local_day(
    catalog: ActivityCatalog,
    user_id: str,
    *,
    year: int,
    month: int,
    display_tz: str,
    source: str | None,
    filters: ActivityFilters | None,
    index: dict[str, SyncIndexEntry],
    by_garmin: dict[int, SyncIndexEntry],
) -> dict[str, list[ActivityBrowseRow]]:
    catalog_rows = catalog.list_for_calendar(user_id, source=source)
    by_day: dict[str, list[ActivityBrowseRow]] = {}
    for row in catalog_rows:
        browse = normalized_to_browse_row(row, index, by_garmin)
        if filters and not _matches_filters(browse, filters, display_tz=display_tz):
            continue
        dt = _parse_iso(row.activity_date or "", tz=display_tz)
        if dt is None or dt.year != year or dt.month != month:
            continue
        iso = dt.date().isoformat()
        by_day.setdefault(iso, []).append(browse)
    for iso in by_day:
        by_day[iso].sort(key=_browse_sort_key)
    return by_day


def _day_stat_from_activities(
    activities: tuple[ActivityBrowseRow, ...],
) -> CalendarDayStat:
    worst: str | None = None
    for act in activities:
        worst = _worst_status(worst, act.sync_status) or worst
    return CalendarDayStat(count=len(activities), worst_status=worst)


def build_activity_calendar(
    ctx: UserContext | None = None,
    user_id: str | None = None,
    *,
    year: int,
    month: int,
    display_tz: str | None,
    prev_href: str,
    next_href: str,
    today_href: str,
    day_list_href,
    selected_from: str = "",
    selected_to: str = "",
    source: str | None = None,
    filters: ActivityFilters | None = None,
    catalog: ActivityCatalog | None = None,
) -> ActivityCalendarView:
    user_ctx = as_context(ctx, user_id)
    cat = catalog or get_catalog(user_ctx)
    uid = user_ctx.user_id
    tz_name = normalize_timezone(display_tz or DEFAULT_TIMEZONE)
    tz = zone_info(tz_name)
    today = datetime.now(tz).date()

    index = cat.build_sync_index(uid)
    by_garmin = {entry.garmin_id: entry for entry in index.values() if entry.garmin_id}
    by_day = _activities_by_local_day(
        cat,
        uid,
        year=year,
        month=month,
        display_tz=tz_name,
        source=source,
        filters=filters,
        index=index,
        by_garmin=by_garmin,
    )

    selected_day = selected_from if selected_from and selected_from == selected_to else ""

    weeks_out: list[tuple[CalendarDayCell, ...]] = []
    total = 0
    for week in cal_mod.Calendar(firstweekday=cal_mod.MONDAY).monthdatescalendar(year, month):
        week_cells: list[CalendarDayCell] = []
        for d in week:
            iso = d.isoformat()
            in_month = d.month == month
            day_acts: tuple[ActivityBrowseRow, ...] = ()
            count = 0
            worst: str | None = None
            if in_month:
                acts = by_day.get(iso, [])
                day_acts = tuple(acts)
                stat = _day_stat_from_activities(day_acts)
                count = stat.count
                worst = stat.worst_status
                total += count
            week_cells.append(
                CalendarDayCell(
                    iso=iso,
                    day_num=d.day,
                    in_month=in_month,
                    count=count,
                    worst_status=worst,
                    is_today=d == today,
                    is_selected=in_month and iso == selected_day,
                    list_href=day_list_href(iso) if in_month else "",
                    activities=day_acts,
                )
            )
        weeks_out.append(tuple(week_cells))

    return ActivityCalendarView(
        year=year,
        month=month,
        month_label=f"{cal_mod.month_name[month]} {year}",
        weekday_labels=("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
        weeks=tuple(weeks_out),
        prev_href=prev_href,
        next_href=next_href,
        today_href=today_href,
        total_in_month=total,
        source_note="From GetSync catalog (SQLite). Cloud-only days may be missing until refresh.",
    )


def attach_calendar_row_views(
    view: ActivityCalendarView,
    row_view,
) -> ActivityCalendarView:
    """Attach template-ready row dicts (menus) to each day cell."""
    weeks_out: list[tuple[CalendarDayCell, ...]] = []
    for week in view.weeks:
        cells: list[CalendarDayCell] = []
        for cell in week:
            rows = tuple(row_view(act) for act in cell.activities)
            cells.append(replace(cell, activity_rows=rows))
        weeks_out.append(tuple(cells))
    return replace(view, weeks=tuple(weeks_out))
