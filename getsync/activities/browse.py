"""Browse Hammerhead / Garmin activities with GetSync sync status."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from getsync.activities.catalog import persist_browse_rows
from getsync.users.context import UserContext, as_context
from getsync.garmin.activities import list_garmin_activities
from getsync.hammerhead.client import HammerheadClient
from getsync.state.store import Store, SyncIndexEntry
from getsync.timeutil import _parse_iso, parse_date_only
from getsync.users.timezones import DEFAULT_TIMEZONE, normalize_timezone

Source = Literal["hammerhead", "garmin"]
SourceFilter = Literal["", "hammerhead", "garmin"]  # "" = all sources
BrowseMode = Literal["all", "hammerhead", "garmin"]

# value → label; substring match against row.activity_type (Garmin type_key, HH type name)
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
MAX_HH_SCAN_PAGES = 25
MAX_GM_SCAN_ITEMS = 500
GM_SCAN_BATCH = 100


@dataclass(frozen=True)
class ActivityFilters:
    q: str = ""
    status: str = ""
    activity_type: str = ""
    date_from: str = ""
    date_to: str = ""
    source: str = ""  # "" = all; hammerhead | garmin

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


def _hh_date(item: dict[str, Any]) -> str | None:
    return item.get("createdAt") or item.get("startDate") or item.get("date")


def _hh_total(payload: dict[str, Any], per_page: int, total_pages: int) -> int:
    for key in ("totalItems", "total", "totalCount", "totalElements"):
        value = payload.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    if total_pages > 0:
        data = payload.get("data") or []
        if total_pages == 1:
            return len(data)
        return (total_pages - 1) * per_page + len(data)
    return len(payload.get("data") or [])


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
        needle = filters.activity_type.strip().lower()
        hay = (row.activity_type or "").lower()
        if needle not in hay:
            return False
    dt = (
        _parse_iso(row.activity_date, tz=display_tz)
        if row.activity_date
        else None
    )
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
    """When listing all sources, skip Garmin rows already shown via Hammerhead link."""
    seen_garmin: set[int] = set()
    out: list[ActivityBrowseRow] = []
    for row in rows:
        if row.source != "hammerhead":
            continue
        out.append(row)
        if row.garmin_id is not None:
            seen_garmin.add(row.garmin_id)
    for row in rows:
        if row.source != "garmin":
            continue
        if row.garmin_id is not None and row.garmin_id in seen_garmin:
            continue
        out.append(row)
    return out


def _browse_mode(filters: ActivityFilters) -> BrowseMode:
    src = filters.source_filter()
    return "all" if not src else src  # type: ignore[return-value]


async def _fetch_unified(
    *,
    page: int,
    per_page: int,
    filters: ActivityFilters,
    ctx: UserContext,
    store: Store,
    display_tz: str,
) -> ActivityBrowsePage:
    mode = _browse_mode(filters)
    src = filters.source_filter()
    index = store.build_sync_index(ctx.user_id)
    errors: list[str] = []
    rows: list[ActivityBrowseRow] = []

    if src in ("", "hammerhead"):
        try:
            rows.extend(await _scan_hammerhead(index, ctx))
        except Exception as exc:
            errors.append(f"Hammerhead: {exc}")

    if src in ("", "garmin"):
        try:
            rows.extend(_scan_garmin(index, ctx))
        except Exception as exc:
            errors.append(f"Garmin: {exc}")

    if not src:
        rows = _dedupe_linked_rows(rows)

    filtered = [row for row in rows if _matches_filters(row, filters, display_tz=display_tz)]
    filtered = _sort_rows_by_date(filtered, display_tz=display_tz)
    persist_browse_rows(store, ctx.user_id, filtered)
    result = _paginate(mode, filtered, page=page, per_page=per_page, filters=filters)
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
    store: Store | None = None,
    display_tz: str | None = None,
) -> ActivityBrowsePage:
    user_ctx = as_context(ctx)
    store = store or Store(user_ctx.db_path)
    filters = filters or ActivityFilters()
    tz = normalize_timezone(display_tz or DEFAULT_TIMEZONE)
    page = max(1, page)
    per_page = min(max(10, per_page), 100)
    src = filters.source_filter()

    if not filters.has_content_filters() and src == "hammerhead":
        index = store.build_sync_index(user_ctx.user_id)
        return await _fetch_hammerhead_native(page, per_page, index, user_ctx, filters)

    if not filters.has_content_filters() and src == "garmin":
        index = store.build_sync_index(user_ctx.user_id)
        return _fetch_garmin_native(page, per_page, index, user_ctx, filters)

    return await _fetch_unified(
        page=page,
        per_page=per_page,
        filters=filters,
        ctx=user_ctx,
        store=store,
        display_tz=tz,
    )


async def _fetch_hammerhead_native(
    page: int,
    per_page: int,
    index: dict[str, SyncIndexEntry],
    ctx: UserContext,
    filters: ActivityFilters,
) -> ActivityBrowsePage:
    hh = HammerheadClient(ctx)
    if hh.load_tokens() is None:
        return ActivityBrowsePage(
            mode="hammerhead",
            rows=[],
            page=page,
            per_page=per_page,
            total=0,
            total_pages=1,
            filters=filters,
            error="Hammerhead not connected",
        )

    try:
        payload = await hh.list_activities(page=page, per_page=per_page)
    except Exception as exc:
        return ActivityBrowsePage(
            mode="hammerhead",
            rows=[],
            page=page,
            per_page=per_page,
            total=0,
            total_pages=1,
            filters=filters,
            error=str(exc),
        )

    total_pages = max(1, int(payload.get("totalPages") or 1))
    total = _hh_total(payload, per_page, total_pages)
    rows = _rows_from_hammerhead(payload.get("data") or [], index)
    persist_browse_rows(Store(user_ctx.db_path), user_ctx.user_id, rows)
    return ActivityBrowsePage(
        mode="hammerhead",
        rows=rows,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        filters=filters,
    )


def _fetch_garmin_native(
    page: int,
    per_page: int,
    index: dict[str, SyncIndexEntry],
    ctx: UserContext,
    filters: ActivityFilters,
) -> ActivityBrowsePage:
    start = (page - 1) * per_page
    try:
        items = list_garmin_activities(limit=per_page, start=start, ctx=ctx)
    except Exception as exc:
        return ActivityBrowsePage(
            mode="garmin",
            rows=[],
            page=page,
            per_page=per_page,
            total=0,
            total_pages=1,
            filters=filters,
            error=str(exc),
        )

    by_garmin = {entry.garmin_id: entry for entry in index.values() if entry.garmin_id}
    rows = _rows_from_garmin(items, by_garmin)
    persist_browse_rows(Store(ctx.db_path), ctx.user_id, rows)
    has_next = len(items) >= per_page
    if has_next:
        total = page * per_page + 1
        total_pages = page + 1
    else:
        total = start + len(items)
        total_pages = page
    return ActivityBrowsePage(
        mode="garmin",
        rows=rows,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=max(1, total_pages),
        filters=filters,
    )


async def _scan_hammerhead(
    index: dict[str, SyncIndexEntry],
    ctx: UserContext,
) -> list[ActivityBrowseRow]:
    hh = HammerheadClient(ctx)
    if hh.load_tokens() is None:
        return []

    rows: list[ActivityBrowseRow] = []
    page = 1
    total_pages = 1
    while page <= total_pages and page <= MAX_HH_SCAN_PAGES:
        payload = await hh.list_activities(page=page, per_page=GM_SCAN_BATCH)
        total_pages = max(1, int(payload.get("totalPages") or 1))
        rows.extend(_rows_from_hammerhead(payload.get("data") or [], index))
        page += 1
    return rows


def _scan_garmin(
    index: dict[str, SyncIndexEntry],
    ctx: UserContext,
) -> list[ActivityBrowseRow]:
    by_garmin = {entry.garmin_id: entry for entry in index.values() if entry.garmin_id}
    rows: list[ActivityBrowseRow] = []
    start = 0
    while start < MAX_GM_SCAN_ITEMS:
        batch = list_garmin_activities(
            limit=GM_SCAN_BATCH, start=start, ctx=ctx
        )
        if not batch:
            break
        rows.extend(_rows_from_garmin(batch, by_garmin))
        if len(batch) < GM_SCAN_BATCH:
            break
        start += GM_SCAN_BATCH
    return rows


def _rows_from_hammerhead(
    items: list[dict[str, Any]],
    index: dict[str, SyncIndexEntry],
) -> list[ActivityBrowseRow]:
    rows: list[ActivityBrowseRow] = []
    for item in items:
        aid = str(item.get("id") or "")
        if not aid:
            continue
        entry = index.get(aid)
        status, detail = _hh_sync_labels(entry)
        rows.append(
            ActivityBrowseRow(
                source="hammerhead",
                external_id=aid,
                name=str(item.get("name") or "—"),
                activity_date=_hh_date(item),
                distance=item.get("distance"),
                duration=item.get("duration"),
                activity_type=_hh_type(item),
                sync_status=status,
                sync_detail=detail,
                hammerhead_id=aid,
                garmin_id=entry.garmin_id if entry else None,
                fit_available=bool(
                    entry and (entry.storage_key or entry.fit_path)
                ),
            )
        )
    return rows


def _hh_type(item: dict[str, Any]) -> str | None:
    raw = item.get("type") or item.get("activityType")
    if isinstance(raw, dict):
        return raw.get("name") or raw.get("type") or str(raw.get("id", ""))
    return str(raw) if raw else None


def _rows_from_garmin(
    items: list[Any],
    by_garmin: dict[int, SyncIndexEntry],
) -> list[ActivityBrowseRow]:
    rows: list[ActivityBrowseRow] = []
    for item in items:
        entry = by_garmin.get(item.activity_id)
        status, detail, hh_id = _garmin_sync_labels(entry)
        rows.append(
            ActivityBrowseRow(
                source="garmin",
                external_id=str(item.activity_id),
                name=item.name,
                activity_date=item.activity_date,
                distance=item.distance,
                duration=item.duration,
                activity_type=item.activity_type,
                sync_status=status,
                sync_detail=detail,
                hammerhead_id=hh_id,
                garmin_id=item.activity_id,
                fit_available=bool(
                    entry and (entry.storage_key or entry.fit_path)
                ),
            )
        )
    return rows


def _hh_sync_labels(entry: SyncIndexEntry | None) -> tuple[str, str | None]:
    if entry is None:
        return "not synced", None
    detail = entry.garmin_upload_status
    if entry.sync_status == "synced":
        return "synced", detail
    if entry.sync_status == "error":
        return "error", entry.error_message
    if entry.sync_status == "pending":
        return "pending", None
    return entry.sync_status, detail


def _garmin_sync_labels(
    entry: SyncIndexEntry | None,
) -> tuple[str, str | None, str | None]:
    if entry is None:
        return "not synced", None, None
    detail = entry.garmin_upload_status
    if entry.sync_status == "synced":
        return "synced", detail, entry.activity_id
    if entry.sync_status == "error":
        return "error", entry.error_message, entry.activity_id
    return entry.sync_status, detail, entry.activity_id
