"""Background catalog refresh for Activities UI (non-blocking HTTP)."""

from __future__ import annotations

import logging
from datetime import date

from getsync.catalog.api import UI_REFRESH_MAX_PAGES, refresh_from_providers
from getsync.timeutil import parse_date_only
from getsync.users.context import resolve_user_context
from getsync.users.timezones import DEFAULT_TIMEZONE, normalize_timezone
from getsync.workspace.application.browse import clear_browse_cache

logger = logging.getLogger("getsync.web.catalog_refresh")


def _optional_filter_date(iso: str, *, display_tz: str) -> date | None:
    raw = iso.strip()
    if not raw:
        return None
    parsed = parse_date_only(raw, tz=display_tz)
    return parsed.date() if parsed is not None else None


async def refresh_activities_catalog_background(
    user_id: str,
    *,
    date_from: str = "",
    date_to: str = "",
    max_pages: int = UI_REFRESH_MAX_PAGES,
) -> None:
    """Pull provider metadata in the background; notify UI via WebSocket."""
    ctx = resolve_user_context(user_id)
    display_tz = DEFAULT_TIMEZONE
    try:
        from getsync.config import get_settings
        from getsync.state.store import Store

        user = Store(get_settings().db_path).get_user(user_id)
        if user and user.timezone:
            display_tz = normalize_timezone(user.timezone)
    except Exception:
        logger.debug("could not resolve user timezone for catalog refresh", exc_info=True)

    try:
        result = await refresh_from_providers(
            ctx,
            date_from=_optional_filter_date(date_from, display_tz=display_tz),
            date_to=_optional_filter_date(date_to, display_tz=display_tz),
            max_pages=max_pages,
        )
        if result.errors:
            logger.warning(
                "catalog refresh user=%s partial errors: %s",
                user_id,
                "; ".join(result.errors),
            )
    except Exception:
        logger.exception("catalog refresh failed user=%s", user_id)
    finally:
        clear_browse_cache(user_id)
        try:
            from getsync.web.realtime import notify_activities_refresh

            await notify_activities_refresh(user_id)
        except Exception:
            logger.debug("activities refresh notify failed", exc_info=True)
