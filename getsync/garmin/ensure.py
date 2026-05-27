"""Garmin session ensure + auto re-login from stored credentials (2.16.2)."""

from __future__ import annotations

import logging

import garth

from getsync.credentials.garmin import load_garmin_login
from getsync.garmin.session import garmin_login, garmin_resume
from getsync.garmin.web_refresh import refresh_web_session
from getsync.garmin.web_session import web_resume
from getsync.users.context import UserContext, as_context

logger = logging.getLogger("getsync.garmin")

_RELOGIN_HINT = (
    "Reconnect Garmin: Settings or `getsync --user {user_id} garmin login` "
    "(use --save-credentials to enable auto re-login)"
)


class GarminSessionError(RuntimeError):
    pass


def _is_oauth_exchange_failure(exc: BaseException) -> bool:
    return "DI-OAuth2 exchange failed" in str(exc)


def _oauth_refresh_expired() -> bool:
    token = garth.client.oauth2_token
    if token is None:
        return True
    if getattr(token, "refresh_expired", False):
        return True
    return False


def try_garmin_auto_login(ctx: UserContext | None = None) -> bool:
    """Re-login with stored email/password if configured."""
    user_ctx = as_context(ctx)
    creds = load_garmin_login(user_ctx)
    if not creds:
        return False
    email, password = creds
    try:
        garmin_login(
            email,
            password,
            user_ctx,
            save_credentials=True,
            store_password=True,
        )
        logger.info("Garmin auto re-login succeeded for user %s", user_ctx.user_id)
        return True
    except Exception as exc:
        logger.warning("Garmin auto re-login failed for %s: %s", user_ctx.user_id, exc)
        return False


def ensure_garmin_web_session(
    ctx: UserContext | None = None,
    *,
    trigger: str = "api",
) -> bool:
    """JWT_WEB valid or refreshed; optional auto login. Returns upload_ready."""
    user_ctx = as_context(ctx)
    if web_resume(user_ctx):
        return True
    result = refresh_web_session(user_ctx, force=False, trigger=trigger)
    if result.get("refreshed") or web_resume(user_ctx):
        return True
    if try_garmin_auto_login(user_ctx):
        return web_resume(user_ctx)
    return False


def ensure_garmin_oauth(ctx: UserContext | None = None) -> None:
    """OAuth (garth) ready for API calls; may auto re-login once."""
    user_ctx = as_context(ctx)
    if garmin_resume(user_ctx) and not _oauth_refresh_expired():
        return
    if try_garmin_auto_login(user_ctx):
        if garmin_resume(user_ctx) and not _oauth_refresh_expired():
            return
    raise GarminSessionError(_RELOGIN_HINT.format(user_id=user_ctx.user_id))


def call_garmin_oauth_api(ctx: UserContext | None, fn):
    """Run garth API callable; on OAuth exchange failure try auto-login once."""
    user_ctx = as_context(ctx)
    last_exc: BaseException | None = None
    for attempt in range(2):
        try:
            ensure_garmin_oauth(user_ctx)
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt == 0 and _is_oauth_exchange_failure(exc) and try_garmin_auto_login(user_ctx):
                continue
            if isinstance(exc, GarminSessionError):
                raise
            if _is_oauth_exchange_failure(exc):
                raise GarminSessionError(_RELOGIN_HINT.format(user_id=user_ctx.user_id)) from exc
            raise
    assert last_exc is not None
    raise last_exc
