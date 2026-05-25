"""Shared context for Jinja cabinet/admin pages."""

from __future__ import annotations

from fastapi import Request

from fit_sinc.web.auth import user_row_from_session
from fit_sinc.web.templating import render_template

APP_PREFIX = "/app"
ADMIN_PREFIX = "/app/admin"

CABINET_NAV = (
    (f"{APP_PREFIX}/", "Dashboard"),
    (f"{APP_PREFIX}/activities", "Activities"),
    (f"{APP_PREFIX}/log", "Sync log"),
    (f"{APP_PREFIX}/session", "Garmin session"),
)


def nav_items_for(user) -> list[tuple[str, str]]:
    items = list(CABINET_NAV)
    if user and user.is_admin:
        items.append((f"{ADMIN_PREFIX}/", "Admin"))
    return items


def _normalize_active(active: str, prefix: str) -> str:
    if not active or active == "/":
        return f"{prefix}/"
    if active.startswith(prefix):
        return active
    return f"{prefix}{active}" if active.startswith("/") else f"{prefix}/{active}"


def cabinet_context(request: Request, *, active: str, wide: bool = False) -> dict:
    user = user_row_from_session(request)
    return {
        "active_nav": _normalize_active(active, APP_PREFIX),
        "nav_items": nav_items_for(user),
        "current_user": user,
        "prefix": APP_PREFIX,
        "admin_prefix": ADMIN_PREFIX,
        "wide": wide,
    }


def render_cabinet(
    request: Request,
    template: str,
    *,
    active: str,
    wide: bool = False,
    **context: object,
) -> str:
    return render_template(
        template,
        **cabinet_context(request, active=active, wide=wide),
        **context,
    )
