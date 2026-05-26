"""User cabinet under /app (session auth)."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from getsync.activities.browse import ActivityFilters, ActivityBrowseRow, fetch_activities_page
from getsync.config import get_settings
from getsync.garmin.web_refresh import refresh_web_session, session_monitor
from getsync.state.store import Store
from getsync.sync.service import sync_activity
from getsync.users.context import UserContext
from getsync.web import html as H
from getsync.web.auth import (
    login_user,
    logout_user,
    user_context_from_session,
    user_row_from_session,
)
from getsync.web.cabinet import render_cabinet
from getsync.web.connections import connection_status
from getsync.web.templating import render_template

logger = logging.getLogger("getsync")
router = APIRouter(prefix="/app", tags=["app"])
P = "/app"


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


def _activities_return_url(
    source: str,
    *,
    page: int = 1,
    per_page: int = 50,
    filters: ActivityFilters | None = None,
    extra: dict[str, str] | None = None,
) -> str:
    params: dict[str, object] = {
        "source": source,
        "page": page,
        "per_page": per_page,
    }
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
    q = H.query_string(params)
    return f"{P}/activities?{q}" if q else f"{P}/activities?source={source}"


@dataclass(frozen=True)
class _ResyncAction:
    activity_id: str
    return_url: str
    force_confirm: bool
    label: str = "Re-sync"


def _activity_row_view(
    row: ActivityBrowseRow,
    source: str,
    *,
    return_url: str,
) -> dict[str, Any]:
    hh_id = row.hammerhead_id
    if source == "hammerhead" and row.hammerhead_id:
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
    if source == "garmin" and row.garmin_id:
        garmin_href = f"https://connect.garmin.com/modern/activity/{row.garmin_id}"

    cross_href = None
    cross_label = None
    cross_external = False
    if source == "hammerhead" and row.garmin_id:
        cross_href = f"https://connect.garmin.com/modern/activity/{row.garmin_id}"
        cross_label = str(row.garmin_id)
        cross_external = True
    elif source == "garmin" and row.hammerhead_id:
        cross_label = row.hammerhead_id

    duration_fmt = (
        H.fmt_duration(row.duration)
        if source == "hammerhead"
        else H.fmt_duration_sec(row.duration)
    )

    return {
        "activity_date": row.activity_date,
        "name": row.name or "—",
        "activity_type": row.activity_type or "—",
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
async def app_login_form(error: str = "") -> str:
    return render_template(
        "pages/app/login.html",
        prefix=P,
        error=bool(error),
    )


@router.post("/login", include_in_schema=False)
async def app_login_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    next: str = Form(""),
) -> RedirectResponse:
    user = _store().verify_user_password(email, password)
    if not user:
        dest = "/?error=1" if (next or "").strip() == "/" else f"{P}/login?error=1"
        return RedirectResponse(dest, status_code=303)
    login_user(request, user.id)
    return RedirectResponse(f"{P}/", status_code=303)


@router.get("/logout", include_in_schema=False)
async def app_logout(request: Request) -> RedirectResponse:
    logout_user(request)
    return RedirectResponse(f"{P}/login", status_code=303)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request) -> str:
    ctx = _ctx(request)
    user = _store().get_user(ctx.user_id)
    store = _store()
    activities = store.list_activities(ctx.user_id, limit=30)
    status_counts = store.count_activities_by_status(ctx.user_id)
    error_n = status_counts.get("error", 0)
    dash_return = f"{P}/"

    activity_rows = []
    for a in activities:
        aid_q = quote(a.activity_id, safe="")
        fit_url = None
        if a.fit_path and Path(a.fit_path).is_file():
            fit_url = f"{P}/activities/{aid_q}/fit"
        resync = _ResyncAction(
            activity_id=a.activity_id,
            return_url=dash_return,
            force_confirm=a.sync_status == "synced",
        )
        activity_rows.append(
            {
                "activity_date": a.activity_date,
                "name": a.name or "—",
                "sync_status": a.sync_status,
                "error_message": a.error_message,
                "distance": a.distance,
                "fit_url": fit_url,
                "resync": resync,
            }
        )

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
        errors_url = (
            f"{P}/activities?"
            f'{H.query_string({"source": "hammerhead", "status": "error"})}'
        )

    return render_cabinet(
        request,
        "pages/app/dashboard.html",
        active="/",
        sync_summary=sync_summary,
        error_count=error_n,
        dash_return=dash_return,
        errors_url=errors_url,
        connections=connection_status(ctx, user),
        activities=activity_rows,
    )


@router.get("/activities", response_class=HTMLResponse, include_in_schema=False)
async def activities_browser(
    request: Request,
    source: str = Query("hammerhead", pattern="^(hammerhead|garmin)$"),
    queued: str = Query(""),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=100),
    q: str = Query(""),
    status: str = Query(""),
    activity_type: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
) -> str:
    ctx = _ctx(request)
    user = _store().get_user(ctx.user_id)
    display_tz = user.timezone if user else None
    filters = ActivityFilters(
        q=q.strip(),
        status=status.strip(),
        activity_type=activity_type.strip(),
        date_from=date_from.strip(),
        date_to=date_to.strip(),
    )
    query_params: dict[str, object] = {
        "source": source,
        "per_page": per_page,
        "q": filters.q,
        "status": filters.status,
        "activity_type": filters.activity_type,
        "date_from": filters.date_from,
        "date_to": filters.date_to,
    }

    result = await fetch_activities_page(
        source,  # type: ignore[arg-type]
        page=page,
        per_page=per_page,
        filters=filters,
        ctx=ctx,
        display_tz=display_tz,
    )
    query_params["page"] = result.page
    list_return = _activities_return_url(
        source, page=result.page, per_page=per_page, filters=filters
    )
    flash = {"queued": queued} if queued else None

    rows = [
        _activity_row_view(row, source, return_url=list_return) for row in result.rows
    ]

    cross_header = "Garmin ID" if source == "hammerhead" else "Hammerhead ID"
    from_idx = (result.page - 1) * result.per_page + 1 if result.total else 0
    to_idx = min(result.page * result.per_page, result.total)
    total_label = f"{from_idx}–{to_idx} of {result.total}"
    if source == "garmin" and not filters.is_active() and result.page == result.total_pages:
        total_label = f"{from_idx}–{to_idx} loaded"

    errors_quick_url = None
    if source == "hammerhead" and filters.status != "error":
        errors_quick_url = (
            f"{P}/activities?"
            f'{H.query_string({"source": "hammerhead", "status": "error", "per_page": per_page})}'
        )

    return render_cabinet(
        request,
        "pages/app/activities.html",
        active="/activities",
        wide=True,
        flash=flash,
        source=source,
        per_page=per_page,
        filters={
            "q": filters.q,
            "status": filters.status,
            "activity_type": filters.activity_type,
            "date_from": filters.date_from,
            "date_to": filters.date_to,
        },
        filters_active=filters.is_active(),
        rows=rows,
        browse_error=result.error,
        cross_header=cross_header,
        total_label=total_label,
        base_path=f"{P}/activities",
        params=query_params,
        page=result.page,
        total_pages=result.total_pages,
        errors_quick_url=errors_quick_url,
    )


@router.get("/log", response_class=HTMLResponse, include_in_schema=False)
async def sync_log(request: Request, page: int = Query(1, ge=1)) -> str:
    ctx = _ctx(request)
    per_page = 50
    store = _store()
    total = store.count_events(user_id=ctx.user_id)
    offset = (page - 1) * per_page
    events = store.list_events(limit=per_page, offset=offset, user_id=ctx.user_id)
    has_next = offset + len(events) < total

    from_idx = offset + 1 if total else 0
    to_idx = offset + len(events)
    return render_cabinet(
        request,
        "pages/app/log.html",
        active="/log",
        events=events,
        page=page,
        prev_page=page - 1 if page > 1 else None,
        next_page=page + 1 if has_next else None,
        range_label=f"{from_idx}–{to_idx} of {total}",
    )


def _session_event_class(event_type: str) -> str:
    if event_type in ("refreshed", "ok"):
        return "ok"
    if event_type in ("failed", "error"):
        return "failed"
    return ""


@router.get("/session", response_class=HTMLResponse, include_in_schema=False)
async def session_monitor_page(request: Request) -> str:
    ctx = _ctx(request)
    mon_raw = session_monitor(ctx)
    events_raw = _store().list_session_refresh_events(limit=150, user_id=ctx.user_id)

    mon = {
        "upload_ready": mon_raw["upload_ready"],
        "upload_label": "ready" if mon_raw["upload_ready"] else "not ready",
        "has_session_cookie": mon_raw["has_session_cookie"],
        "jwt_valid": mon_raw["jwt_valid"],
        "needs_refresh": mon_raw["needs_refresh"],
        "expires_at": mon_raw["expires_at"],
        "ttl_sec": mon_raw["ttl_sec"],
        "refreshed_at": mon_raw["refreshed_at"],
        "refresh_method": mon_raw.get("refresh_method") or "",
        "interval_min": mon_raw["refresh_interval_sec"] // 60,
        "before_h": mon_raw["refresh_before_sec"] // 3600,
    }
    events = [
        {
            "created_at": e.created_at,
            "trigger": e.trigger,
            "event_type": e.event_type,
            "message": e.message,
            "status_class": _session_event_class(e.event_type),
        }
        for e in events_raw
    ]

    return render_cabinet(
        request,
        "pages/app/session.html",
        active="/session",
        mon=mon,
        events=events,
    )


@router.post("/session/refresh", include_in_schema=False)
async def session_refresh_now(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    await asyncio.to_thread(refresh_web_session, ctx, force=True, trigger="web")
    return RedirectResponse(url=f"{P}/session", status_code=303)


@router.get("/activities/{activity_id}/fit", include_in_schema=False)
async def download_fit(request: Request, activity_id: str) -> FileResponse:
    ctx = _ctx(request)
    row = _store().get_activity(ctx.user_id, activity_id)
    if row and row.fit_path and Path(row.fit_path).is_file():
        return FileResponse(
            row.fit_path,
            media_type="application/vnd.ant.fit",
            filename=Path(row.fit_path).name,
        )
    candidate = ctx.fits_dir / f"{activity_id.replace('/', '_')}.fit"
    if candidate.is_file():
        return FileResponse(
            candidate,
            media_type="application/vnd.ant.fit",
            filename=candidate.name,
        )
    raise HTTPException(status_code=404, detail="FIT file not found")


@router.post("/activities/{activity_id}/retry", include_in_schema=False)
async def retry_activity(
    request: Request,
    activity_id: str,
    background_tasks: BackgroundTasks,
    next: str = Form(""),
) -> RedirectResponse:
    ctx = _ctx(request)
    default = _activities_return_url("hammerhead")
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
    failed = store.list_activities(ctx.user_id, limit=50, sync_status="error")
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
        "hammerhead",
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
