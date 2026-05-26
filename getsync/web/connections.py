"""Hammerhead + Garmin connection status for dashboard banner and settings."""

from __future__ import annotations

import time
from typing import Any

from getsync.config import get_settings
from getsync.garmin.session import garmin_status
from getsync.garmin.web_refresh import session_monitor
from getsync.hammerhead.client import HammerheadClient
from getsync.users.context import UserContext
from getsync.users.models import UserRow


def connection_status(ctx: UserContext, user: UserRow | None = None) -> dict[str, Any]:
    """Structured HH + Garmin state for dashboard banner."""
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
        "session_path": "/session",
    }


def connection_settings_view(ctx: UserContext, user: UserRow) -> dict[str, object]:
    """Flat dict for settings.html (backward compatible)."""
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
