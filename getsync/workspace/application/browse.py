"""Activity list page: read catalog snapshot, filter, paginate."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from getsync.catalog.api import get_catalog, refresh_from_providers
from getsync.contracts.persistence import ActivityCatalog
from getsync.timeutil import _parse_iso, parse_date_only
from getsync.users.context import UserContext, as_context
from getsync.users.timezones import DEFAULT_TIMEZONE, normalize_timezone
from getsync.workspace.application.mapping import normalized_to_browse_row
from getsync.workspace.domain.filters import ActivityFilters, BrowseMode, activity_type_matches
from getsync.workspace.domain.rows import ActivityBrowsePage, ActivityBrowseRow

BROWSE_CACHE_TTL_SEC = 300


@dataclass
class _CachedBrowse:
    expires_at: float
    mode: BrowseMode
    rows: list[ActivityBrowseRow]
    errors: list[str]


_BROWSE_CACHE: dict[str, _CachedBrowse] = {}


def browse_cache_key(user_id: str, filters: ActivityFilters, display_tz: str) -> str:
    return "|".join(
        (
            user_id,
            display_tz,
            filters.q,
            filters.status,
            filters.activity_type,
            filters.date_from,
            filters.date_to,
            filters.source,
        )
    )


def clear_browse_cache(user_id: str | None = None) -> None:
    if user_id is None:
        _BROWSE_CACHE.clear()
        return
    prefix = f"{user_id}|"
    for key in list(_BROWSE_CACHE):
        if key.startswith(prefix):
            del _BROWSE_CACHE[key]


def _browse_mode(filters: ActivityFilters) -> BrowseMode:
    src = filters.source_filter()
    return "all" if not src else src  # type: ignore[return-value]


def _matches_filters(
    row: ActivityBrowseRow,
    filters: ActivityFilters,
    *,
    display_tz: str,
) -> bool:
    if filters.q.strip():
        if filters.q.strip().lower() not in row.name.lower():
            return False
    if filters.source.strip():
        if row.source != filters.source.strip().lower():
            return False
    if filters.status.strip():
        if row.sync_status != filters.status.strip():
            return False
    if filters.activity_type.strip():
        if not activity_type_matches(filters.activity_type, row.activity_type):
            return False
    dt = _parse_iso(row.activity_date, tz=display_tz) if row.activity_date else None
    if filters.date_from.strip():
        start = parse_date_only(filters.date_from.strip(), tz=display_tz)
        if start and (dt is None or dt.date() < start.date()):
            return False
    if filters.date_to.strip():
        end = parse_date_only(filters.date_to.strip(), tz=display_tz)
        if end and (dt is None or dt.date() > end.date()):
            return False
    return True


def _paginate(
    mode: BrowseMode,
    rows: list[ActivityBrowseRow],
    *,
    page: int,
    per_page: int,
    filters: ActivityFilters,
) -> ActivityBrowsePage:
    total = len(rows)
    total_pages = max(1, math.ceil(total / per_page)) if total else 1
    page = min(max(1, page), total_pages)
    start = (page - 1) * per_page
    end = start + per_page
    return ActivityBrowsePage(
        mode=mode,
        rows=rows[start:end],
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        filters=filters,
    )


def _sort_rows_by_date(
    rows: list[ActivityBrowseRow],
    *,
    display_tz: str,
) -> list[ActivityBrowseRow]:
    def key(row: ActivityBrowseRow) -> float:
        dt = _parse_iso(row.activity_date, tz=display_tz) if row.activity_date else None
        return dt.timestamp() if dt is not None else 0.0

    return sorted(rows, key=key, reverse=True)


def _dedupe_linked_rows(rows: list[ActivityBrowseRow]) -> list[ActivityBrowseRow]:
    """When listing all sources, skip Garmin rows already shown via Hammerhead link.

    Other sources (e.g. Strava) are kept; only HH↔Garmin pairing is deduplicated.
    """
    seen_garmin: set[int] = set()
    hammerhead_rows: list[ActivityBrowseRow] = []
    garmin_rows: list[ActivityBrowseRow] = []
    other_rows: list[ActivityBrowseRow] = []
    for row in rows:
        if row.source == "hammerhead":
            hammerhead_rows.append(row)
            if row.garmin_id is not None:
                seen_garmin.add(row.garmin_id)
        elif row.source == "garmin":
            garmin_rows.append(row)
        else:
            other_rows.append(row)
    out = list(hammerhead_rows)
    for row in garmin_rows:
        if row.garmin_id is not None and row.garmin_id in seen_garmin:
            continue
        out.append(row)
    out.extend(other_rows)
    return out


def _load_rows_from_catalog(
    *,
    filters: ActivityFilters,
    catalog: ActivityCatalog,
    user_id: str,
    display_tz: str,
) -> tuple[BrowseMode, list[ActivityBrowseRow]]:
    mode = _browse_mode(filters)
    src = filters.source_filter()
    source = src if src else None
    index = catalog.build_sync_index(user_id)
    by_garmin = {entry.garmin_id: entry for entry in index.values() if entry.garmin_id}

    catalog_rows = catalog.list_for_browse(user_id, source=source)
    rows = [
        normalized_to_browse_row(row, index, by_garmin)
        for row in catalog_rows
    ]

    if not src:
        rows = _dedupe_linked_rows(rows)

    filtered = [row for row in rows if _matches_filters(row, filters, display_tz=display_tz)]
    filtered = _sort_rows_by_date(filtered, display_tz=display_tz)
    return mode, filtered


def _page_from_rows(
    *,
    mode: BrowseMode,
    rows: list[ActivityBrowseRow],
    errors: list[str],
    page: int,
    per_page: int,
    filters: ActivityFilters,
) -> ActivityBrowsePage:
    result = _paginate(mode, rows, page=page, per_page=per_page, filters=filters)
    if errors and not result.rows:
        return ActivityBrowsePage(
            mode=mode,
            rows=[],
            page=page,
            per_page=per_page,
            total=0,
            total_pages=1,
            filters=filters,
            error="; ".join(errors),
        )
    if errors:
        return ActivityBrowsePage(
            mode=result.mode,
            rows=result.rows,
            page=result.page,
            per_page=result.per_page,
            total=result.total,
            total_pages=result.total_pages,
            filters=result.filters,
            error="; ".join(errors),
        )
    return result


async def fetch_activities_page(
    *,
    page: int = 1,
    per_page: int = 50,
    filters: ActivityFilters | None = None,
    ctx: UserContext | None = None,
    catalog: ActivityCatalog | None = None,
    display_tz: str | None = None,
    refresh: bool = False,
) -> ActivityBrowsePage:
    user_ctx = as_context(ctx)
    cat = catalog or get_catalog(user_ctx)
    filters = filters or ActivityFilters()
    tz = normalize_timezone(display_tz or DEFAULT_TIMEZONE)
    page = max(1, page)
    per_page = min(max(10, per_page), 100)

    errors: list[str] = []
    if refresh:
        clear_browse_cache(user_ctx.user_id)
        refresh_result = await refresh_from_providers(user_ctx, catalog=cat)
        errors.extend(refresh_result.errors)

    key = browse_cache_key(user_ctx.user_id, filters, tz)
    if not refresh:
        cached = _BROWSE_CACHE.get(key)
        if cached and cached.expires_at > time.monotonic():
            return _page_from_rows(
                mode=cached.mode,
                rows=cached.rows,
                errors=cached.errors,
                page=page,
                per_page=per_page,
                filters=filters,
            )

    mode, rows = _load_rows_from_catalog(
        filters=filters,
        catalog=cat,
        user_id=user_ctx.user_id,
        display_tz=tz,
    )
    _BROWSE_CACHE[key] = _CachedBrowse(
        time.monotonic() + BROWSE_CACHE_TTL_SEC,
        mode,
        rows,
        errors,
    )
    return _page_from_rows(
        mode=mode,
        rows=rows,
        errors=errors,
        page=page,
        per_page=per_page,
        filters=filters,
    )
