"""Shared context for Jinja cabinet/admin pages."""

from __future__ import annotations

from fastapi import Request

from getsync.users.locale import DEFAULT_LOCALE, normalize_locale
from getsync.users.timezones import DEFAULT_TIMEZONE
from getsync.web.app_i18n import cabinet_strings
from getsync.web.auth import user_row_from_session
from getsync.web.templating import render_template

APP_PREFIX = "/app"
ADMIN_PREFIX = "/app/admin"

_NAV_KEYS = (
    ("nav_activities", f"{APP_PREFIX}/activities"),
    ("nav_dashboard", f"{APP_PREFIX}/"),
    ("nav_settings", f"{APP_PREFIX}/settings"),
)


def nav_items_for(user, lang: str) -> list[tuple[str, str]]:
    t = cabinet_strings(lang)
    items = [(href, t[key]) for key, href in _NAV_KEYS]
    if user and user.is_admin:
        items.append((f"{ADMIN_PREFIX}/", t["nav_admin"]))
    return items


def _normalize_active(active: str, prefix: str) -> str:
    if not active or active == "/":
        return f"{prefix}/"
    if active.startswith(prefix):
        return active
    return f"{prefix}{active}" if active.startswith("/") else f"{prefix}/{active}"


def cabinet_context(request: Request, *, active: str, wide: bool = False) -> dict:
    user = user_row_from_session(request)
    lang = normalize_locale(user.locale if user else DEFAULT_LOCALE)
    display_tz = user.timezone if user else DEFAULT_TIMEZONE
    t = cabinet_strings(lang)
    return {
        "active_nav": _normalize_active(active, APP_PREFIX),
        "nav_items": nav_items_for(user, lang),
        "current_user": user,
        "user_timezone": display_tz,
        "display_timezone": display_tz,
        "lang": lang,
        "t": t,
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
    ctx = cabinet_context(request, active=active, wide=wide)
    display_tz = ctx.pop("display_timezone")
    return render_template(
        template,
        display_timezone=display_tz,
        **ctx,
        **context,
    )
