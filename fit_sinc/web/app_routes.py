"""User cabinet under /app (session auth)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from fit_sinc.activities.browse import ActivityFilters, fetch_activities_page
from fit_sinc.config import get_settings
from fit_sinc.garmin.session import garmin_status
from fit_sinc.garmin.web_refresh import refresh_web_session, session_monitor
from fit_sinc.hammerhead.client import HammerheadClient
from fit_sinc.state.store import Store
from fit_sinc.sync.service import sync_activity
from fit_sinc.users.context import UserContext
from fit_sinc.web import html as H
from fit_sinc.web.auth import login_user, logout_user, user_context_from_session

logger = logging.getLogger("fit_sinc")
router = APIRouter(prefix="/app", tags=["app"])
P = "/app"


def _store() -> Store:
    return Store(get_settings().db_path)


def _ctx(request: Request) -> UserContext:
    ctx = user_context_from_session(request)
    if not ctx:
        raise HTTPException(status_code=401)
    return ctx


def _fit_sinc_status_class(status: str) -> str:
    if status == "synced":
        return "status-synced"
    if status == "error":
        return "status-error"
    if status == "pending":
        return "status-pending"
    if status == "not synced":
        return "status-not-synced"
    return ""


def _render_activity_actions(row: Any, source: str) -> str:
    parts: list[str] = []
    if source == "hammerhead" and row.hammerhead_id:
        aid_q = quote(row.hammerhead_id, safe="")
        if row.fit_available:
            parts.append(f'<a class="btn" href="{P}/activities/{aid_q}/fit">.fit</a>')
        if row.fit_sinc_status != "synced":
            parts.append(
                f"""<form class="inline" method="post" action="{P}/activities/{aid_q}/retry">
              <button class="btn" type="submit">sync</button></form>"""
            )
    if source == "garmin" and row.garmin_id:
        gid = row.garmin_id
        parts.append(
            f'<a class="btn" href="https://connect.garmin.com/modern/activity/{gid}" '
            f'target="_blank" rel="noopener">Garmin</a>'
        )
        if row.hammerhead_id and row.fit_available:
            aid_q = quote(row.hammerhead_id, safe="")
            parts.append(f'<a class="btn" href="{P}/activities/{aid_q}/fit">.fit</a>')
    return " ".join(parts)


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def app_login_form(error: str = "") -> str:
    err = f'<p class="err">Invalid email or password</p>' if error else ""
    body = f"""
  <h2>Sign in</h2>
  {err}
  <form method="post" action="{P}/login" class="filters" style="max-width: 360px;">
    <label>Email <input type="email" name="email" required autocomplete="username"></label>
    <label>Password <input type="password" name="password" required autocomplete="current-password"></label>
    <button class="btn" type="submit">Sign in</button>
  </form>
"""
    return f"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<title>Login — fit_sinc</title><style>{H.BASE_CSS}</style></head><body>
<header class="hero"><img src="/static/icon.svg" width="48" height="48" alt=""><h1>fit_sinc</h1></header>
{body}</body></html>"""


@router.post("/login", include_in_schema=False)
async def app_login_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
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


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard(request: Request) -> str:
    ctx = _ctx(request)
    user = _store().get_user(ctx.user_id)
    now = H.fmt_now()
    hh = HammerheadClient(ctx).status()
    gm = garmin_status(ctx)
    activities = _store().list_activities(ctx.user_id, limit=30)

    hh_class = "ok" if hh.get("connected") else "warn"
    if gm.get("upload_ready"):
        gm_label = "upload ready"
        gm_class = "ok"
    elif gm.get("connected"):
        gm_label = "oauth only (run garmin login for upload)"
        gm_class = "warn"
    else:
        gm_label = "not connected"
        gm_class = "warn"

    rows = []
    for a in activities:
        aid_q = quote(a.activity_id, safe="")
        status_cls = f"status-{a.sync_status}"
        fit_link = ""
        if a.fit_path and Path(a.fit_path).is_file():
            fit_link = f'<a class="btn" href="{P}/activities/{aid_q}/fit">.fit</a>'
        retry = ""
        if a.sync_status in ("error", "pending"):
            retry = f"""<form class="inline" method="post" action="{P}/activities/{aid_q}/retry">
              <button class="btn" type="submit">retry</button></form>"""
        err_tip = f' title="{H.esc(a.error_message)}"' if a.error_message else ""
        rows.append(
            f"<tr>"
            f"<td>{H.fmt_date(a.activity_date)}</td>"
            f"<td>{H.esc(a.name)}</td>"
            f'<td class="{status_cls}"{err_tip}>{H.esc(a.sync_status)}</td>'
            f"<td>{H.fmt_km(a.distance)}</td>"
            f"<td>{fit_link} {retry}</td>"
            f"</tr>"
        )
    if not rows:
        rows.append(
            '<tr><td colspan="5"><em>No activities yet — waiting for webhook or run backfill.</em></td></tr>'
        )

    who = user.display_name if user else ctx.user_id
    body = f"""
  <p>Hammerhead → Garmin Connect · <strong>{H.esc(who)}</strong></p>

  <h2>Connections</h2>
  <table>
    <tr><th>Hammerhead</th><td class="{hh_class}">{"connected" if hh.get("connected") else "not connected"}</td></tr>
    <tr><th>Garmin</th><td class="{gm_class}">{H.esc(gm_label)}</td></tr>
  </table>

  <h2>Recent activities</h2>
  <table>
    <tr><th>Date</th><th>Name</th><th>Status</th><th>Distance</th><th>Actions</th></tr>
    {"".join(rows)}
  </table>
  <p><small>Updated {H.esc(now)} · TZ {H.esc(user.timezone if user else "—")}</small></p>
"""
    return H.page("Dashboard", body, active="/", prefix=P)


@router.get("/activities", response_class=HTMLResponse, include_in_schema=False)
async def activities_browser(
    request: Request,
    source: str = Query("hammerhead", pattern="^(hammerhead|garmin)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=10, le=100),
    q: str = Query(""),
    status: str = Query(""),
    activity_type: str = Query(""),
    date_from: str = Query(""),
    date_to: str = Query(""),
) -> str:
    ctx = _ctx(request)
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
    )

    hh_active = "active" if source == "hammerhead" else ""
    gm_active = "active" if source == "garmin" else ""
    rows: list[str] = []
    for row in result.rows:
        status_cls = _fit_sinc_status_class(row.fit_sinc_status)
        err_tip = f' title="{H.esc(row.fit_sinc_detail)}"' if row.fit_sinc_detail else ""
        duration = (
            H.fmt_duration(row.duration)
            if source == "hammerhead"
            else H.fmt_duration_sec(row.duration)
        )
        cross = "—"
        if source == "hammerhead" and row.garmin_id:
            cross = f'<a href="https://connect.garmin.com/modern/activity/{row.garmin_id}" target="_blank" rel="noopener">{row.garmin_id}</a>'
        elif source == "garmin" and row.hammerhead_id:
            cross = f'<span class="mono">{H.esc(row.hammerhead_id)}</span>'

        detail = ""
        if row.fit_sinc_detail and row.fit_sinc_status == "synced":
            detail = f' <small>({H.esc(row.fit_sinc_detail)})</small>'

        rows.append(
            f"<tr>"
            f"<td>{H.fmt_datetime(row.activity_date)}</td>"
            f"<td>{H.esc(row.name)}</td>"
            f"<td>{H.esc(row.activity_type)}</td>"
            f"<td>{H.fmt_km(row.distance)}</td>"
            f"<td>{duration}</td>"
            f'<td class="{status_cls}"{err_tip}>{H.esc(row.fit_sinc_status)}{detail}</td>'
            f"<td>{cross}</td>"
            f"<td>{_render_activity_actions(row, source)}</td>"
            f"</tr>"
        )

    if result.error:
        rows = [f'<tr><td colspan="8" class="err">{H.esc(result.error)}</td></tr>']
    elif not rows:
        rows.append('<tr><td colspan="8"><em>No activities match filters.</em></td></tr>')

    cross_header = "Garmin ID" if source == "hammerhead" else "Hammerhead ID"
    from_idx = (result.page - 1) * result.per_page + 1 if result.total else 0
    to_idx = min(result.page * result.per_page, result.total)
    total_label = f"{from_idx}–{to_idx} of {result.total}"
    if source == "garmin" and not filters.is_active() and result.page == result.total_pages:
        total_label = f"{from_idx}–{to_idx} loaded"

    pager = H.render_pager(f"{P}/activities", query_params, page=result.page, total_pages=result.total_pages)
    reset_q = H.query_string({"source": source, "per_page": per_page})

    body = f"""
  <h2>Activities</h2>
  <p>Hammerhead / Garmin with fit_sinc sync status.</p>

  <div class="tabs">
    <a href="{P}/activities?{H.query_string({"source": "hammerhead", "per_page": per_page})}" class="{hh_active}">Hammerhead</a>
    <a href="{P}/activities?{H.query_string({"source": "garmin", "per_page": per_page})}" class="{gm_active}">Garmin</a>
  </div>

  <form class="filters" method="get" action="{P}/activities">
    <input type="hidden" name="source" value="{H.esc(source)}">
    <label>Name <input type="search" name="q" value="{H.esc(filters.q)}" placeholder="Morning Ride"></label>
    <label>fit_sinc
      <select name="status">
        <option value="">all</option>
        <option value="synced"{" selected" if filters.status == "synced" else ""}>synced</option>
        <option value="not synced"{" selected" if filters.status == "not synced" else ""}>not synced</option>
        <option value="pending"{" selected" if filters.status == "pending" else ""}>pending</option>
        <option value="error"{" selected" if filters.status == "error" else ""}>error</option>
      </select>
    </label>
    <label>Type <input type="text" name="activity_type" value="{H.esc(filters.activity_type)}" placeholder="cycling"></label>
    <label>From <input type="date" name="date_from" value="{H.esc(filters.date_from)}"></label>
    <label>To <input type="date" name="date_to" value="{H.esc(filters.date_to)}"></label>
    <label>Per page
      <select name="per_page">
        <option value="25"{" selected" if per_page == 25 else ""}>25</option>
        <option value="50"{" selected" if per_page == 50 else ""}>50</option>
        <option value="100"{" selected" if per_page == 100 else ""}>100</option>
      </select>
    </label>
    <div class="filters-actions">
      <button class="btn" type="submit">Filter</button>
      <a class="btn" href="{P}/activities?{reset_q}">Reset</a>
    </div>
  </form>

  <p><small>{total_label}{" · filters active" if filters.is_active() else ""}</small></p>

  <div class="table-wrap">
  <table>
    <tr>
      <th>Date / time</th><th>Name</th><th>Type</th><th>Distance</th><th>Duration</th>
      <th>fit_sinc</th><th>{cross_header}</th><th>Actions</th>
    </tr>
    {"".join(rows)}
  </table>
  </div>
  <div class="pager">{pager}</div>
  <p><small>Updated {H.esc(H.fmt_now())}</small></p>
"""
    return H.page("Activities", body, active="/activities", wide=True, prefix=P)


@router.get("/log", response_class=HTMLResponse, include_in_schema=False)
async def sync_log(request: Request, page: int = Query(1, ge=1)) -> str:
    ctx = _ctx(request)
    per_page = 50
    store = _store()
    total = store.count_events(user_id=ctx.user_id)
    offset = (page - 1) * per_page
    events = store.list_events(limit=per_page, offset=offset, user_id=ctx.user_id)
    has_next = offset + len(events) < total

    prev_link = f'<a class="btn" href="{P}/log?page={page - 1}">← Prev</a>' if page > 1 else ""
    next_link = f'<a class="btn" href="{P}/log?page={page + 1}">Next →</a>' if has_next else ""

    rows = []
    for e in events:
        rows.append(
            f"<tr>"
            f'<td class="mono">{H.fmt_date(e.created_at)}</td>'
            f"<td>{H.esc(e.event_type)}</td>"
            f'<td class="mono">{H.esc(e.activity_id)}</td>'
            f"<td>{H.esc(e.message)}</td>"
            f"</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="4"><em>No events yet.</em></td></tr>')

    from_idx = offset + 1 if total else 0
    to_idx = offset + len(events)
    body = f"""
  <h2>Sync log</h2>
  <p><small>{from_idx}–{to_idx} of {total}</small></p>
  <table>
    <tr><th>Time</th><th>Event</th><th>Activity</th><th>Message</th></tr>
    {"".join(rows)}
  </table>
  <div class="pager">{prev_link}<span>Page {page}</span>{next_link}</div>
"""
    return H.page("Sync log", body, active="/log", prefix=P)


def _session_event_class(event_type: str) -> str:
    if event_type in ("refreshed", "ok"):
        return "status-ok"
    if event_type in ("failed", "error"):
        return "status-failed"
    return ""


@router.get("/session", response_class=HTMLResponse, include_in_schema=False)
async def session_monitor_page(request: Request) -> str:
    ctx = _ctx(request)
    mon = session_monitor(ctx)
    events = _store().list_session_refresh_events(limit=150, user_id=ctx.user_id)

    ready_cls = "status-ok" if mon["upload_ready"] else "status-failed"
    ready_label = "ready" if mon["upload_ready"] else "not ready"
    session_cls = "status-ok" if mon["has_session_cookie"] else "status-failed"
    jwt_cls = "status-ok" if mon["jwt_valid"] else "status-failed"
    needs_cls = "status-warn" if mon["needs_refresh"] else "status-ok"

    log_rows = []
    for e in events:
        cls = _session_event_class(e.event_type)
        log_rows.append(
            f"<tr>"
            f'<td class="mono">{H.fmt_date(e.created_at)}</td>'
            f"<td>{H.esc(e.trigger)}</td>"
            f'<td class="{cls}">{H.esc(e.event_type)}</td>'
            f"<td>{H.esc(e.message)}</td>"
            f"</tr>"
        )
    if not log_rows:
        log_rows.append('<tr><td colspan="4"><em>No refresh events yet.</em></td></tr>')

    interval_min = mon["refresh_interval_sec"] // 60
    before_h = mon["refresh_before_sec"] // 3600
    body = f"""
  <h2>Garmin web session</h2>
  <p>Automatic JWT_WEB refresh for FIT upload (Playwright).</p>
  <div class="panel">
  <h3>Status</h3>
  <table>
    <tr><th>Upload</th><td class="{ready_cls}">{H.esc(ready_label)}</td></tr>
    <tr><th>Session cookie</th><td class="{session_cls}">{"present" if mon["has_session_cookie"] else "missing"}</td></tr>
    <tr><th>JWT valid</th><td class="{jwt_cls}">{"yes" if mon["jwt_valid"] else "no"}</td></tr>
    <tr><th>Needs refresh</th><td class="{needs_cls}">{"yes" if mon["needs_refresh"] else "no"}</td></tr>
    <tr><th>JWT expires</th><td>{H.fmt_ts(mon["expires_at"])} <small>(in {H.fmt_ttl(mon["ttl_sec"])})</small></td></tr>
    <tr><th>Last refresh</th><td>{H.fmt_ts(mon["refreshed_at"])} {H.esc(mon["refresh_method"] or "")}</td></tr>
    <tr><th>Background check</th><td>every {interval_min} min</td></tr>
    <tr><th>Refresh before expiry</th><td>{before_h} h</td></tr>
  </table>
  <form method="post" action="{P}/session/refresh" style="margin-top: 1rem;">
    <button class="btn" type="submit">Refresh now</button>
  </form>
  </div>
  <h3>Refresh log</h3>
  <table>
    <tr><th>Time</th><th>Trigger</th><th>Event</th><th>Message</th></tr>
    {"".join(log_rows)}
  </table>
  <p><small>Updated {H.esc(H.fmt_now())}</small></p>
"""
    return H.page("Garmin session", body, active="/session", prefix=P)


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
) -> RedirectResponse:
    ctx = _ctx(request)
    background_tasks.add_task(_run_sync_force, activity_id, ctx.user_id)
    return RedirectResponse(url=f"{P}/activities?source=hammerhead", status_code=303)


async def _run_sync_force(activity_id: str, user_id: str) -> None:
    try:
        await sync_activity(activity_id, force=True, user_id=user_id)
    except Exception:
        logger.exception("retry sync failed for %s user=%s", activity_id, user_id)
