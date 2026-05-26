"""User cabinet under /app (session auth)."""

from __future__ import annotations

import asyncio
import calendar as cal_mod
import logging
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from getsync.activities.browse import (
    ACTIVITY_TYPE_FILTER_CHOICES,
    BROWSE_CACHE_TTL_SEC,
    ActivityFilters,
    ActivityBrowseRow,
    fetch_activities_page,
)
from getsync.activities.calendar import build_activity_calendar
from getsync.timeutil import zone_info
from getsync.users.timezones import DEFAULT_TIMEZONE, normalize_timezone
from getsync.config import get_settings
from getsync.state.store import Store
from getsync.sync.service import sync_activity
from getsync.users.bootstrap import registration_is_open
from getsync.users.context import UserContext
from getsync.web import html as H
from getsync.web.app_i18n import auth_strings
from getsync.web.auth import (
    login_user,
    logout_user,
    user_context_from_session,
    user_row_from_session,
)
from getsync.web.cabinet import render_cabinet
from getsync.web.connections import connection_settings_view
from getsync.web.site_i18n import LANG_COOKIE, lang_from_request, landing_strings
from getsync.storage.activity import ActivityStorage
from getsync.web.templating import render_template

logger = logging.getLogger("getsync")
router = APIRouter(prefix="/app", tags=["app"])
P = "/app"
_LANG_COOKIE_MAX_AGE = 365 * 24 * 3600


def _set_lang_cookie(response: RedirectResponse | HTMLResponse, lang: str) -> None:
    response.set_cookie(
        LANG_COOKIE,
        lang,
        max_age=_LANG_COOKIE_MAX_AGE,
        httponly=False,
        samesite="lax",
    )


def _store() -> Store:
    return Store(get_settings().db_path)


def _ctx(request: Request) -> UserContext:
    ctx = user_context_from_session(request)
    if not ctx:
        raise HTTPException(status_code=401)
    return ctx


def _safe_return_url(next_url: str, default: str) -> str:
    n = (next_url or "").strip()
    if n.startswith(P + "/") or n in (P, f"{P}/"):
        return n
    return default


def _activities_query_params(
    *,
    page: int = 1,
    per_page: int = 50,
    filters: ActivityFilters | None = None,
    view: str = "list",
    year: int | None = None,
    month: int | None = None,
    extra: dict[str, str] | None = None,
) -> dict[str, object]:
    params: dict[str, object] = {
        "per_page": per_page,
        "view": view,
    }
    if view == "list":
        params["page"] = page
    if view == "calendar" and year is not None and month is not None:
        params["year"] = year
        params["month"] = month
    if filters and filters.source.strip():
        params["source"] = filters.source.strip()
    if filters:
        if filters.q:
            params["q"] = filters.q
        if filters.status:
            params["status"] = filters.status
        if filters.activity_type:
            params["activity_type"] = filters.activity_type
        if filters.date_from:
            params["date_from"] = filters.date_from
        if filters.date_to:
            params["date_to"] = filters.date_to
    if extra:
        params.update(extra)
    return params


def _activities_return_url(
    *,
    page: int = 1,
    per_page: int = 50,
    filters: ActivityFilters | None = None,
    view: str = "list",
    year: int | None = None,
    month: int | None = None,
    extra: dict[str, str] | None = None,
) -> str:
    params = _activities_query_params(
        page=page,
        per_page=per_page,
        filters=filters,
        view=view,
        year=year,
        month=month,
        extra=extra,
    )
    q = H.query_string(params)
    return f"{P}/activities?{q}" if q else f"{P}/activities"


def _activities_rows_load_url(
    *,
    per_page: int,
    filters: ActivityFilters | None = None,
) -> str:
    """Base URL for infinite-scroll row fragments (page added by JS)."""
    params = _activities_query_params(
        page=1,
        per_page=per_page,
        filters=filters,
        view="list",
    )
    params.pop("page", None)
    q = H.query_string(params)
    return f"{P}/activities/rows?{q}" if q else f"{P}/activities/rows"


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    m = month + delta
    y = year
    while m < 1:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return y, m


def _month_date_bounds(year: int, month: int) -> tuple[str, str]:
    last = cal_mod.monthrange(year, month)[1]
    return f"{year}-{month:02d}-01", f"{year}-{month:02d}-{last:02d}"


def _format_filter_date_display(iso: str) -> str:
    try:
        return date.fromisoformat(iso).strftime("%d.%m.%Y")
    except ValueError:
        return iso


def _activities_subheader_context(
    *,
    view: str,
    filters: ActivityFilters,
    cal_year: int,
    cal_month: int,
    per_page: int,
    page: int,
    today: date,
) -> dict[str, object]:
    ref_year, ref_month = (
        (cal_year, cal_month) if view == "calendar" else (today.year, today.month)
    )
    month_start, month_end = _month_date_bounds(ref_year, ref_month)
    picker_from = filters.date_from or month_start
    picker_to = filters.date_to or month_end

    type_label = "all types"
    type_links: list[dict[str, object]] = []
    for value, label in ACTIVITY_TYPE_FILTER_CHOICES:
        active = (filters.activity_type or "") == value
        if active:
            type_label = label.lower() if value else "all types"
        nf = ActivityFilters(
            q=filters.q,
            status=filters.status,
            activity_type=value,
            date_from=filters.date_from,
            date_to=filters.date_to,
            source=filters.source,
        )
        type_links.append(
            {
                "href": _activities_return_url(
                    page=1,
                    per_page=per_page,
                    filters=nf,
                    view=view,
                    year=cal_year if view == "calendar" else None,
                    month=cal_month if view == "calendar" else None,
                    extra={"refresh": "1"},
                ),
                "label": label,
                "active": active,
            }
        )

    return {
        "picker_date_from": picker_from,
        "picker_date_to": picker_to,
        "subheader_date_from": _format_filter_date_display(picker_from),
        "subheader_date_to": _format_filter_date_display(picker_to),
        "subheader_type_label": type_label,
        "type_filter_links": type_links,
    }


def _activities_tab_query_factory(
    base: dict[str, object],
) -> Callable[[str], str]:
    def tab_query(view_name: str) -> str:
        params = {k: v for k, v in base.items() if k not in ("page", "year", "month", "view")}
        params["view"] = view_name
        if view_name == "calendar":
            y = base.get("year")
            m = base.get("month")
            if y is not None and m is not None:
                params["year"] = y
                params["month"] = m
        return H.query_string(params)

    return tab_query


@dataclass(frozen=True)
class _ResyncAction:
    activity_id: str
    return_url: str
    force_confirm: bool
    label: str = "Re-sync"


_SOURCE_LABELS = {"hammerhead": "Hammerhead", "garmin": "Garmin"}


def _activity_row_view(
    row: ActivityBrowseRow,
    *,
    return_url: str,
) -> dict[str, Any]:
    hh_id = row.hammerhead_id

    fit_url = None
    resync = None
    garmin_href = None
    if hh_id:
        aid_q = quote(hh_id, safe="")
        if row.fit_available:
            fit_url = f"{P}/activities/{aid_q}/fit"
        resync = _ResyncAction(
            activity_id=hh_id,
            return_url=return_url,
            force_confirm=row.sync_status == "synced",
        )
    if row.garmin_id:
        garmin_href = f"https://connect.garmin.com/modern/activity/{row.garmin_id}"

    cross_href = None
    cross_label = None
    cross_external = False
    if row.garmin_id:
        cross_href = garmin_href
        cross_label = str(row.garmin_id)
        cross_external = True
    elif row.hammerhead_id and row.source == "garmin":
        cross_label = row.hammerhead_id

    duration_fmt = (
        H.fmt_duration(row.duration)
        if row.source == "hammerhead"
        else H.fmt_duration_sec(row.duration)
    )

    return {
        "activity_date": row.activity_date,
        "name": row.name or "—",
        "source": row.source,
        "source_label": _SOURCE_LABELS.get(row.source, row.source),
        "activity_type": (
            "cycling" if row.source == "hammerhead" else (row.activity_type or "—")
        ),
        "distance": row.distance,
        "duration_fmt": duration_fmt,
        "sync_status": row.sync_status,
        "sync_detail": row.sync_detail,
        "cross_href": cross_href,
        "cross_label": cross_label,
        "cross_external": cross_external,
        "fit_url": fit_url,
        "resync": resync,
        "garmin_href": garmin_href,
    }


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def app_login_form(
    request: Request,
    error: str = "",
    lang: str | None = Query(None),
) -> HTMLResponse:
    resolved = lang_from_request(request, lang)
    lang_next = f"{P}/login" + ("?error=1" if error else "")
    response = HTMLResponse(
        render_template(
            "pages/app/login.html",
            prefix=P,
            error=bool(error),
            registration_open=registration_is_open(),
            lang=resolved,
            lang_next_path=lang_next,
            active_nav="login",
            t=landing_strings(resolved),
            form_t=auth_strings(resolved),
        )
    )
    if lang is not None:
        _set_lang_cookie(response, resolved)
    return response


@router.post("/login", include_in_schema=False)
async def app_login_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    next: str = Form(""),
) -> RedirectResponse:
    user = _store().verify_user_password(email, password)
    if not user:
        return RedirectResponse(f"{P}/login?error=1", status_code=303)
    login_user(request, user.id)
    return RedirectResponse(f"{P}/", status_code=303)


@router.get("/logout", include_in_schema=False)
async def app_logout(request: Request) -> RedirectResponse:
    logout_user(request)
    return RedirectResponse(f"{P}/login", status_code=303)


_PREVIEW_PAGES: list[tuple[str, str, str]] = [
    (f"{P}/ui-preview", "Overview", "All wireframe screens"),
    (f"{P}/ui-preview/dashboard", "Dashboard", "Recent activities table"),
    (f"{P}/ui-preview/activities", "Activities", "Calendar + filters + table"),
    (f"{P}/ui-preview/settings", "Settings", "Profile, connections, password"),
    (f"{P}/ui-preview/admin", "Admin", "Users list"),
]

_PREVIEW_TEMPLATES: dict[str, tuple[str, str]] = {
    "dashboard": ("pages/app/ui_preview_dashboard.html", f"{P}/"),
    "activities": ("pages/app/ui_preview_activities.html", f"{P}/activities"),
    "settings": ("pages/app/ui_preview_settings.html", f"{P}/settings"),
    "admin": ("pages/app/ui_preview_admin.html", f"{P}/admin/"),
}


def _render_ui_preview(
    request: Request,
    template: str,
    *,
    active: str,
    **extra: object,
) -> str:
    ctx = _ctx(request)
    user = _store().get_user(ctx.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return render_cabinet(
        request,
        template,
        active=active,
        preview_pages=_PREVIEW_PAGES,
        settings_section="profile",
        **extra,
    )


@router.get("/ui-preview", response_class=HTMLResponse, include_in_schema=False)
async def ui_preview_index(request: Request) -> str:
    """Layout wireframes (no form fields) — local design review."""
    return _render_ui_preview(
        request,
        "pages/app/ui_preview_index.html",
        active=f"{P}/ui-preview",
    )


@router.get("/ui-preview/{page_name}", response_class=HTMLResponse, include_in_schema=False)
async def ui_preview_page(request: Request, page_name: str) -> str:
    spec = _PREVIEW_TEMPLATES.get(page_name)
    if spec is None:
        raise HTTPException(status_code=404, detail="unknown preview page")
    template, active = spec
    extra: dict[str, object] = {}
    if page_name == "activities":
        ctx = _ctx(request)
        store = _store()
        user = store.get_user(ctx.user_id)
        tz_name = normalize_timezone(user.timezone if user else DEFAULT_TIMEZONE)
        today = datetime.now(zone_info(tz_name)).date()
        extra["calendar"] = build_activity_calendar(
            store,
            ctx.user_id,
            year=today.year,
            month=today.month,
            display_tz=user.timezone if user else None,
            prev_href="#",
            next_href="#",
            today_href="#",
            day_list_href=lambda _d: "#",
        )
    return _render_ui_preview(request, template, active=active, **extra)


def _sync_log_context(store: Store, user_id: str, log_page: int) -> dict[str, object]:
    per_page = 50
    total = store.count_events(user_id=user_id)
    offset = (log_page - 1) * per_page
    events = store.list_events(limit=per_page, offset=offset, user_id=user_id)
    has_next = offset + len(events) < total
    from_idx = offset + 1 if total else 0
    to_idx = offset + len(events)
    return {
        "log_events": events,
        "log_page": log_page,
        "log_prev_page": log_page - 1 if log_page > 1 else None,
        "log_next_page": log_page + 1 if has_next else None,
        "log_range_label": f"{from_idx}–{to_idx} of {total}",
    }


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(
    request: Request,
    log_page: int = Query(1, ge=1),
) -> str:
    ctx = _ctx(request)
    user = _store().get_user(ctx.user_id)
    store = _store()
    status_counts = store.count_activities_by_status(ctx.user_id, source="hammerhead")
    catalog_total = store.count_catalog(ctx.user_id)
    error_n = status_counts.get("error", 0)
    dash_return = f"{P}/"

    sync_bits = []
    for label, key in (
        ("synced", "synced"),
        ("error", "error"),
        ("pending", "pending"),
        ("not synced", "not synced"),
    ):
        n = status_counts.get(key, 0)
        if n:
            sync_bits.append(f"{label}: {n}")
    sync_summary = ", ".join(sync_bits) if sync_bits else "no activities in DB yet"

    errors_url = None
    if error_n:
        errors_url = f"{P}/activities?{H.query_string({'status': 'error'})}"

    return render_cabinet(
        request,
        "pages/app/dashboard.html",
        active="/",
        sync_summary=sync_summary,
        catalog_total=catalog_total,
        error_count=error_n,
        dash_return=dash_return,
        errors_url=errors_url,
        activities_url=f"{P}/activities",
        **_sync_log_context(store, ctx.user_id, log_page),
    )


@router.get("/activities", response_class=HTMLResponse, include_in_schema=False)
async def activities_browser(
    request: Request,
    view: str = Query("list", pattern="^(list|calendar)$"),
    source: str = Query("", pattern="^(|hammerhead|garmin)$"),
    queued: str = Query(""),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=100),
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    q: str = Query(""),
    status: str = Query(""),
    activity_type: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
    refresh: str = Query(""),
) -> str:
    ctx = _ctx(request)
    store = _store()
    user = store.get_user(ctx.user_id)
    display_tz = user.timezone if user else None
    filters = ActivityFilters(
        q=q.strip(),
        status=status.strip(),
        activity_type=activity_type.strip(),
        date_from=date_from.strip(),
        date_to=date_to.strip(),
        source=source.strip().lower(),
    )
    tz_name = normalize_timezone(display_tz or DEFAULT_TIMEZONE)
    today = datetime.now(zone_info(tz_name)).date()
    cal_year = year if year is not None else today.year
    cal_month = month if month is not None else today.month

    base_params = _activities_query_params(
        per_page=per_page,
        filters=filters,
        view=view,
        year=cal_year if view == "calendar" else None,
        month=cal_month if view == "calendar" else None,
    )
    tab_query = _activities_tab_query_factory(base_params)
    flash = {"queued": queued} if queued else None

    common = dict(
        activities_view=view,
        activities_tab_query=tab_query,
        per_page=per_page,
        filters={
            "q": filters.q,
            "status": filters.status,
            "activity_type": filters.activity_type,
            "date_from": filters.date_from,
            "date_to": filters.date_to,
            "source": filters.source,
        },
        filters_active=filters.is_active(),
        activity_type_choices=ACTIVITY_TYPE_FILTER_CHOICES,
        filter_form_id="activities-filter-form",
        **_activities_subheader_context(
            view=view,
            filters=filters,
            cal_year=cal_year,
            cal_month=cal_month,
            per_page=per_page,
            page=page,
            today=today,
        ),
    )

    if view == "calendar":
        src = filters.source or None

        def day_list_href(day_iso: str) -> str:
            day_filters = ActivityFilters(
                q=filters.q,
                status=filters.status,
                activity_type=filters.activity_type,
                date_from=day_iso,
                date_to=day_iso,
                source=filters.source,
            )
            return _activities_return_url(
                page=1,
                per_page=per_page,
                filters=day_filters,
                view="list",
            )

        calendar = build_activity_calendar(
            store,
            ctx.user_id,
            year=cal_year,
            month=cal_month,
            display_tz=display_tz,
            prev_href=_activities_return_url(
                per_page=per_page,
                filters=filters,
                view="calendar",
                year=_shift_month(cal_year, cal_month, -1)[0],
                month=_shift_month(cal_year, cal_month, -1)[1],
            ),
            next_href=_activities_return_url(
                per_page=per_page,
                filters=filters,
                view="calendar",
                year=_shift_month(cal_year, cal_month, 1)[0],
                month=_shift_month(cal_year, cal_month, 1)[1],
            ),
            today_href=_activities_return_url(
                per_page=per_page,
                filters=filters,
                view="calendar",
                year=today.year,
                month=today.month,
            ),
            day_list_href=day_list_href,
            selected_from=filters.date_from,
            selected_to=filters.date_to,
            source=src,
        )
        return render_cabinet(
            request,
            "pages/app/activities.html",
            active="/activities",
            wide=True,
            app_main_class="getsync-app-main--activities",
            flash=flash,
            calendar=calendar,
            **common,
        )

    bust_cache = refresh.strip() in ("1", "true", "yes")
    result = await fetch_activities_page(
        page=page,
        per_page=per_page,
        filters=filters,
        ctx=ctx,
        display_tz=display_tz,
        refresh=bust_cache,
    )
    query_params = _activities_query_params(
        page=result.page,
        per_page=per_page,
        filters=filters,
        view="list",
    )
    list_return = _activities_return_url(
        page=result.page, per_page=per_page, filters=filters, view="list"
    )

    rows = [_activity_row_view(row, return_url=list_return) for row in result.rows]

    from_idx = (result.page - 1) * result.per_page + 1 if result.total else 0
    to_idx = min(result.page * result.per_page, result.total)
    total_label = f"{from_idx}–{to_idx} of {result.total}"
    if (
        result.mode == "garmin"
        and not filters.has_content_filters()
        and result.page == result.total_pages
    ):
        total_label = f"{from_idx}–{to_idx} loaded"

    tab_base = _activities_query_params(
        per_page=per_page,
        filters=filters,
        view="list",
        page=result.page,
        year=today.year,
        month=today.month,
    )

    has_more = result.page < result.total_pages

    return render_cabinet(
        request,
        "pages/app/activities.html",
        active="/activities",
        wide=True,
        app_main_class="getsync-app-main--activities",
        flash=flash,
        rows=rows,
        browse_error=result.error,
        total_label=total_label,
        base_path=f"{P}/activities",
        params=query_params,
        page=result.page,
        total_pages=result.total_pages,
        rows_load_url=_activities_rows_load_url(per_page=per_page, filters=filters),
        next_page=result.page + 1,
        has_more_rows=has_more,
        data_source_hint=(
            "Hammerhead & Garmin APIs · metadata in SQLite · "
            f"list cached {BROWSE_CACHE_TTL_SEC // 60} min"
        ),
        activities_tab_query=_activities_tab_query_factory(tab_base),
        **{k: v for k, v in common.items() if k != "activities_tab_query"},
    )


@router.get("/activities/rows", include_in_schema=False)
async def activities_rows_fragment(
    request: Request,
    source: str = Query("", pattern="^(|hammerhead|garmin)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=100),
    q: str = Query(""),
    status: str = Query(""),
    activity_type: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
) -> HTMLResponse:
    """HTML fragment: table rows for infinite scroll."""
    ctx = _ctx(request)
    store = _store()
    user = store.get_user(ctx.user_id)
    display_tz = user.timezone if user else None
    filters = ActivityFilters(
        q=q.strip(),
        status=status.strip(),
        activity_type=activity_type.strip(),
        date_from=date_from.strip(),
        date_to=date_to.strip(),
        source=source.strip().lower(),
    )
    result = await fetch_activities_page(
        page=page,
        per_page=per_page,
        filters=filters,
        ctx=ctx,
        display_tz=display_tz,
    )
    list_return = _activities_return_url(
        page=result.page, per_page=per_page, filters=filters, view="list"
    )
    rows = [_activity_row_view(row, return_url=list_return) for row in result.rows]
    has_more = result.page < result.total_pages
    html = render_template(
        "components/activities_table_rows.html",
        rows=rows,
        has_more_rows=has_more,
    )
    return HTMLResponse(
        html,
        headers={
            "X-Next-Page": str(result.page + 1),
            "X-Has-More": "1" if has_more else "0",
        },
    )


@router.get("/log", include_in_schema=False)
async def sync_log_redirect(request: Request, page: int = Query(1, ge=1)) -> RedirectResponse:
    """Legacy URL — sync log lives on the dashboard."""
    _ctx(request)
    return RedirectResponse(f"{P}/?log_page={page}#sync-log", status_code=303)


@router.get("/session", include_in_schema=False)
async def session_page_redirect(request: Request) -> RedirectResponse:
    """Legacy URL — Garmin session monitor lives in Settings."""
    _ctx(request)
    return RedirectResponse(f"{P}/settings#garmin-session", status_code=303)


@router.post("/session/refresh", include_in_schema=False)
async def session_refresh_legacy(request: Request) -> RedirectResponse:
    """Legacy POST — same as Settings → Refresh now."""
    from getsync.garmin.web_refresh import refresh_web_session

    ctx = _ctx(request)
    await asyncio.to_thread(refresh_web_session, ctx, force=True, trigger="web")
    return RedirectResponse(f"{P}/settings?msg=garmin_refreshed#garmin-session", status_code=303)


@router.get("/activities/{activity_id}/fit", include_in_schema=False)
async def download_fit(request: Request, activity_id: str) -> FileResponse:
    ctx = _ctx(request)
    storage = ActivityStorage(ctx)
    row = _store().get_activity(ctx.user_id, activity_id, source="hammerhead")
    fit_file: Path | None = None
    if row:
        fit_file = storage.open_fit_path(row.storage_key)
        if fit_file is None and row.fit_path:
            legacy = Path(row.fit_path)
            if legacy.is_file():
                fit_file = legacy
    if fit_file is None:
        candidate = storage.legacy_fit_path(activity_id)
        if candidate.is_file():
            fit_file = candidate
    if fit_file is None:
        raise HTTPException(status_code=404, detail="FIT file not found")
    return FileResponse(
        fit_file,
        media_type="application/vnd.ant.fit",
        filename=fit_file.name,
    )


@router.post("/activities/{activity_id}/retry", include_in_schema=False)
async def retry_activity(
    request: Request,
    activity_id: str,
    background_tasks: BackgroundTasks,
    next: str = Form(""),
) -> RedirectResponse:
    ctx = _ctx(request)
    default = _activities_return_url()
    background_tasks.add_task(_run_sync_force, activity_id, ctx.user_id)
    _store().log_event(
        "resync_queued",
        "manual single",
        activity_id,
        user_id=ctx.user_id,
    )
    return RedirectResponse(url=_safe_return_url(next, default), status_code=303)


@router.post("/activities/retry-errors", include_in_schema=False)
async def retry_all_errors(
    request: Request,
    background_tasks: BackgroundTasks,
    next: str = Form(""),
) -> RedirectResponse:
    ctx = _ctx(request)
    store = _store()
    failed = store.list_activities(
        ctx.user_id, limit=50, sync_status="error", source="hammerhead"
    )
    for row in failed:
        background_tasks.add_task(_run_sync_force, row.activity_id, ctx.user_id)
    if failed:
        store.log_event(
            "resync_queued",
            f"manual bulk count={len(failed)}",
            None,
            user_id=ctx.user_id,
        )
    default = _activities_return_url(
        filters=ActivityFilters(status="error"),
        extra={"queued": str(len(failed))},
    )
    target = _safe_return_url(next, default)
    if failed and "queued=" not in target:
        sep = "&" if "?" in target else "?"
        target = f"{target}{sep}queued={len(failed)}"
    return RedirectResponse(url=target, status_code=303)


async def _run_sync_force(activity_id: str, user_id: str) -> None:
    try:
        await sync_activity(activity_id, force=True, user_id=user_id)
    except Exception:
        logger.exception("retry sync failed for %s user=%s", activity_id, user_id)
