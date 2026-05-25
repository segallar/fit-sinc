"""UI v2 (Jinja2 + Tailwind + HTMX) — отдельный роутер, не трогает html.py-страницы."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from fit_sinc.config import get_settings
from fit_sinc.garmin.session import garmin_status
from fit_sinc.garmin.web_refresh import session_monitor
from fit_sinc.hammerhead.client import HammerheadClient
from fit_sinc.state.store import Store
from fit_sinc.web import html as H
from fit_sinc.web.templating import render_template

logger = logging.getLogger("fit_sinc")

router = APIRouter(tags=["ui-v2"])

_PREVIEW_NAV = [
    ("", "Dashboard (v1)"),
    ("/activities", "Activities (v1)"),
    ("/ui-preview", "UI v2 preview"),
]


def _store() -> Store:
    return Store(get_settings().db_path)


def _safe_list_activities(limit: int = 8) -> list:
    try:
        return _store().list_activities(limit=limit)
    except Exception as exc:
        logger.debug("ui-preview: activities unavailable (%s)", exc)
        return []


def _demo_activity_rows() -> list[dict]:
    return [
        {
            "date": "2026-05-20T10:00:00+03:00",
            "name": "Morning Ride (demo)",
            "status": "synced",
            "detail": None,
            "distance_m": 42_500.0,
        },
        {
            "date": "2026-05-19T18:30:00+03:00",
            "name": "Evening Gravel (demo)",
            "status": "error",
            "detail": "Garmin upload timeout",
            "distance_m": 61_200.0,
        },
    ]


@router.get("/ui-preview", response_class=HTMLResponse, include_in_schema=False)
async def ui_preview() -> str:
    hh = HammerheadClient().status()
    gm = garmin_status()
    activities = _safe_list_activities(limit=8)

    if gm.get("upload_ready"):
        gm_label = "upload ready"
    elif gm.get("connected"):
        gm_label = "oauth only"
    else:
        gm_label = "not connected"

    if activities:
        rows = [
            {
                "date": a.activity_date,
                "name": a.name or "—",
                "status": a.sync_status,
                "detail": a.error_message,
                "distance_m": a.distance,
            }
            for a in activities
        ]
    else:
        rows = _demo_activity_rows()

    return render_template(
        "pages/ui_preview.html",
        nav_items=_PREVIEW_NAV,
        active_nav="/ui-preview",
        hh_connected=bool(hh.get("connected")),
        gm_upload_ready=bool(gm.get("upload_ready")),
        gm_label=gm_label,
        activity_rows=rows,
    )


@router.get(
    "/ui-preview/fragment/status",
    response_class=HTMLResponse,
    include_in_schema=False,
)
async def ui_preview_status_fragment() -> str:
    try:
        mon = session_monitor(None)
        ttl = H.fmt_ttl(mon.get("ttl_sec"))
    except Exception as exc:
        logger.debug("ui-preview fragment: session monitor unavailable (%s)", exc)
        ttl = "—"
    try:
        count = len(_store().list_activities(limit=500))
    except Exception:
        count = 0
    return render_template(
        "fragments/status_panel.html",
        jwt_ttl=ttl,
        activity_count=count,
    )
