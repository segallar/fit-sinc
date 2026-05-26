"""Connection registry: sources and sinks (many per user)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

from getsync.config import get_settings
from getsync.garmin.session import garmin_status
from getsync.garmin.web_refresh import session_monitor
from getsync.state.store import Store
from getsync.hammerhead.client import HammerheadClient
from getsync.users.context import UserContext
from getsync.users.models import UserRow

ConnectionRole = Literal["source", "sink"]


@dataclass(frozen=True)
class ConnectionDetail:
    label: str
    value: str
    mono: bool = False


@dataclass(frozen=True)
class ConnectionItem:
    """One row in Settings → Connections (extensible list)."""

    id: str
    role: ConnectionRole
    role_label: str
    name: str
    status_text: str
    status_variant: str  # success | warning | secondary
    details: tuple[ConnectionDetail, ...]
    actions_template: str | None = None
    available: bool = True


@dataclass(frozen=True)
class ConnectionGroups:
    sources: tuple[ConnectionItem, ...]
    sinks: tuple[ConnectionItem, ...]


def connection_status(ctx: UserContext, user: UserRow | None = None) -> dict[str, Any]:
    """Structured HH + Garmin state (legacy banner / helpers)."""
    hh = HammerheadClient(ctx).status()
    gm = garmin_status(ctx)
    mon = session_monitor(ctx)
    oauth = gm.get("oauth") or {}
    web = gm.get("web") or {}

    hh_connected = bool(hh.get("connected"))
    hh_expires = float(hh["expires_at"]) if hh_connected and hh.get("expires_at") else None
    hh_ttl_sec: float | None = None
    if hh_expires is not None:
        hh_ttl_sec = max(0.0, hh_expires - time.time())

    upload_ready = bool(mon.get("upload_ready"))
    jwt_ttl_sec = mon.get("ttl_sec")
    jwt_expires = mon.get("expires_at")

    return {
        "hammerhead": {
            "connected": hh_connected,
            "expired": bool(hh.get("expired")),
            "expires_at": hh_expires,
            "ttl_sec": hh_ttl_sec,
            "user_id": (user.hammerhead_user_id if user else None) or hh.get("user_id"),
            "oauth_configured": bool(get_settings().hammerhead_client_id),
        },
        "garmin": {
            "upload_ready": upload_ready,
            "oauth_connected": bool(oauth.get("connected")),
            "web_connected": bool(web.get("connected")),
            "jwt_valid": bool(mon.get("jwt_valid")),
            "needs_refresh": bool(mon.get("needs_refresh")),
            "has_session_cookie": bool(mon.get("has_session_cookie")),
            "expires_at": jwt_expires,
            "ttl_sec": jwt_ttl_sec,
            "web_reason": web.get("reason") or "",
        },
        "settings_path": "/settings",
        "session_path": "/settings#garmin-session",
    }


def _session_event_class(event_type: str) -> str:
    if event_type in ("refreshed", "ok"):
        return "ok"
    if event_type in ("failed", "error"):
        return "failed"
    return ""


def _garmin_session_monitor(mon_raw: dict[str, object]) -> dict[str, object]:
    return {
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


def garmin_session_context(ctx: UserContext) -> dict[str, object]:
    """Garmin JWT monitor for Settings (status + manual refresh)."""
    return {"mon": _garmin_session_monitor(session_monitor(ctx))}


def garmin_refresh_log_context(
    store: Store,
    *,
    user_id: str | None = None,
    limit: int = 200,
) -> dict[str, object]:
    """JWT refresh event log (admin: all users; optional filter by user_id)."""
    users_by_id = {u.id: u for u in store.list_users()}
    events_raw = store.list_session_refresh_events(limit=limit, user_id=user_id)
    events = [
        {
            "created_at": e.created_at,
            "user_id": e.user_id,
            "user_label": (
                users_by_id[e.user_id].slug
                if e.user_id and e.user_id in users_by_id
                else (e.user_id or "—")
            ),
            "trigger": e.trigger,
            "event_type": e.event_type,
            "message": e.message,
            "status_class": _session_event_class(e.event_type),
        }
        for e in events_raw
    ]
    return {"garmin_session_events": events}


def list_connections(ctx: UserContext, user: UserRow) -> ConnectionGroups:
    """All connection slots for Settings UI (implemented + planned)."""
    status = connection_status(ctx, user)
    hh = status["hammerhead"]
    gm = status["garmin"]
    from getsync.web import html as H

    fmt = H.make_formatter(user.timezone)
    jwt_exp = gm.get("expires_at")

    hh_status = "connected" if hh["connected"] else "not connected"
    hh_variant = "success" if hh["connected"] else "warning"

    gm_status = "ready" if gm["upload_ready"] else "not ready"
    gm_variant = "success" if gm["upload_ready"] else "warning"

    sources: list[ConnectionItem] = [
        ConnectionItem(
            id="hammerhead",
            role="source",
            role_label="Source",
            name="Hammerhead",
            status_text=hh_status,
            status_variant=hh_variant,
            details=(
                ConnectionDetail("Webhook user id", str(hh.get("user_id") or "—"), mono=True),
            ),
            actions_template="components/connections/hammerhead_actions.html",
        ),
        ConnectionItem(
            id="strava",
            role="source",
            role_label="Source",
            name="Strava",
            status_text="planned",
            status_variant="secondary",
            details=(),
            available=False,
        ),
        ConnectionItem(
            id="wahoo",
            role="source",
            role_label="Source",
            name="Wahoo",
            status_text="planned",
            status_variant="secondary",
            details=(),
            available=False,
        ),
    ]

    sinks: list[ConnectionItem] = [
        ConnectionItem(
            id="garmin",
            role="sink",
            role_label="Destination",
            name="Garmin Connect",
            status_text=gm_status,
            status_variant=gm_variant,
            details=(
                ConnectionDetail(
                    "Web session",
                    "ok" if gm["web_connected"] else str(gm.get("web_reason") or "—"),
                ),
                ConnectionDetail(
                    "JWT expires",
                    fmt.fmt_ts(jwt_exp) if jwt_exp else "—",
                ),
                ConnectionDetail(
                    "OAuth (garth)",
                    "connected" if gm["oauth_connected"] else "—",
                ),
            ),
            actions_template="components/connections/garmin_actions.html",
        ),
    ]

    return ConnectionGroups(sources=tuple(sources), sinks=tuple(sinks))


def connection_settings_view(ctx: UserContext, user: UserRow) -> dict[str, object]:
    """Flat dict for connection action partials (backward compatible)."""
    status = connection_status(ctx, user)
    hh = status["hammerhead"]
    gm = status["garmin"]
    jwt_exp = gm.get("expires_at")
    from getsync.web import html as H

    return {
        "hh_connected": hh["connected"],
        "hh_user_id": hh.get("user_id") or "—",
        "hh_expired": hh.get("expired"),
        "hh_path": str(ctx.hammerhead_tokens_path),
        "garmin_upload_ready": gm["upload_ready"],
        "garmin_oauth": gm["oauth_connected"],
        "garmin_web": gm["web_connected"],
        "garmin_jwt_expires": H.make_formatter(user.timezone).fmt_ts(jwt_exp)
        if jwt_exp
        else "—",
        "garmin_web_reason": gm.get("web_reason") or "—",
        "hammerhead_oauth_configured": hh["oauth_configured"],
    }
