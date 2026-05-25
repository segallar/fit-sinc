"""Browse Hammerhead / Garmin activities with fit_sinc sync status."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from fit_sinc.users.context import UserContext, as_context
from fit_sinc.garmin.activities import list_garmin_activities
from fit_sinc.hammerhead.client import HammerheadClient
from fit_sinc.state.store import Store, SyncIndexEntry
from fit_sinc.timeutil import _parse_iso, parse_date_only

Source = Literal["hammerhead", "garmin"]
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

    def is_active(self) -> bool:
        return bool(
            self.q.strip()
            or self.status.strip()
            or self.activity_type.strip()
            or self.date_from.strip()
            or self.date_to.strip()
        )


@dataclass(frozen=True)
class ActivityBrowseRow:
    source: Source
    external_id: str
    name: str
    activity_date: str | None
    distance: float | None
    duration: float | None
    activity_type: str | None
    fit_sinc_status: str
    fit_sinc_detail: str | None
    hammerhead_id: str | None
    garmin_id: int | None
    fit_available: bool


@dataclass(frozen=True)
class ActivityBrowsePage:
    source: Source
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


def _matches_filters(row: ActivityBrowseRow, filters: ActivityFilters) -> bool:
    if filters.q.strip():
        if filters.q.strip().lower() not in row.name.lower():
            return False
    if filters.status.strip():
        if row.fit_sinc_status != filters.status.strip():
            return False
    if filters.activity_type.strip():
        needle = filters.activity_type.strip().lower()
        hay = (row.activity_type or "").lower()
        if needle not in hay:
            return False
    dt = _parse_iso(row.activity_date) if row.activity_date else None
    if filters.date_from.strip():
        start = parse_date_only(filters.date_from.strip())
        if start and (dt is None or dt.date() < start.date()):
            return False
    if filters.date_to.strip():
        end = parse_date_only(filters.date_to.strip())
        if end and (dt is None or dt.date() > end.date()):
            return False
    return True


def _paginate(
    source: Source,
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
        source=source,
        rows=rows[start:end],
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        filters=filters,
    )


async def fetch_activities_page(
    source: Source,
    *,
    page: int = 1,
    per_page: int = 50,
    filters: ActivityFilters | None = None,
    ctx: UserContext | None = None,
    store: Store | None = None,
) -> ActivityBrowsePage:
    user_ctx = as_context(ctx)
    store = store or Store(user_ctx.db_path)
    filters = filters or ActivityFilters()
    page = max(1, page)
    per_page = min(max(10, per_page), 100)

    if filters.is_active():
        try:
            if source == "hammerhead":
                rows = await _scan_hammerhead(
                    index := store.build_sync_index(user_ctx.user_id), user_ctx
                )
            else:
                rows = _scan_garmin(
                    index := store.build_sync_index(user_ctx.user_id), user_ctx
                )
        except Exception as exc:
            return ActivityBrowsePage(
                source, [], page, per_page, 0, 1, filters, error=str(exc)
            )
        filtered = [row for row in rows if _matches_filters(row, filters)]
        return _paginate(source, filtered, page=page, per_page=per_page, filters=filters)

    index = store.build_sync_index(user_ctx.user_id)
    if source == "hammerhead":
        return await _fetch_hammerhead_native(page, per_page, index, user_ctx, filters)
    return _fetch_garmin_native(page, per_page, index, user_ctx, filters)


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
            "hammerhead", [], page, per_page, 0, 1, filters, error="Hammerhead not connected"
        )

    try:
        payload = await hh.list_activities(page=page, per_page=per_page)
    except Exception as exc:
        return ActivityBrowsePage(
            "hammerhead", [], page, per_page, 0, 1, filters, error=str(exc)
        )

    total_pages = max(1, int(payload.get("totalPages") or 1))
    total = _hh_total(payload, per_page, total_pages)
    rows = _rows_from_hammerhead(payload.get("data") or [], index)
    return ActivityBrowsePage(
        source="hammerhead",
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
            "garmin", [], page, per_page, 0, 1, filters, error=str(exc)
        )

    by_garmin = {entry.garmin_id: entry for entry in index.values() if entry.garmin_id}
    rows = _rows_from_garmin(items, by_garmin)
    has_next = len(items) >= per_page
    if has_next:
        total = page * per_page + 1
        total_pages = page + 1
    else:
        total = start + len(items)
        total_pages = page
    return ActivityBrowsePage(
        source="garmin",
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
                fit_sinc_status=status,
                fit_sinc_detail=detail,
                hammerhead_id=aid,
                garmin_id=entry.garmin_id if entry else None,
                fit_available=bool(entry and entry.fit_path),
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
                fit_sinc_status=status,
                fit_sinc_detail=detail,
                hammerhead_id=hh_id,
                garmin_id=item.activity_id,
                fit_available=bool(entry and entry.fit_path),
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
