import io
import logging
from pathlib import Path
from typing import Any

import garth

from getsync.config import Settings, get_settings
from getsync.users.context import UserContext, as_context
from getsync.garmin.browser_upload import upload_fit_via_browser
from getsync.garmin.web_session import (
    upload_fit_via_web,
    web_login,
    web_resume,
    web_status,
)
from getsync.garmin.web_refresh import ensure_web_session

logger = logging.getLogger("getsync.garmin")


def _garth_dir(ctx: UserContext | None = None) -> Path:
    return as_context(ctx).garth_dir


def garmin_login(email: str, password: str, ctx: UserContext | None = None) -> None:
    user_ctx = as_context(ctx)
    garth_dir = _garth_dir(user_ctx)
    garth_dir.mkdir(parents=True, exist_ok=True)
    try:
        garth.login(email, password)
        garth.save(str(garth_dir))
    except Exception as exc:
        if garmin_resume(user_ctx):
            logger.warning("Garmin OAuth login failed, keeping existing session: %s", exc)
        else:
            raise
    web_login(email, password, user_ctx)


def garmin_resume(ctx: UserContext | None = None) -> bool:
    garth_dir = _garth_dir(ctx)
    if not garth_dir.is_dir():
        return False
    try:
        garth.resume(str(garth_dir))
        return garth.client.oauth2_token is not None
    except Exception:
        return False


def garmin_status(ctx: UserContext | None = None) -> dict[str, Any]:
    user_ctx = as_context(ctx)
    garth_dir = _garth_dir(user_ctx)
    oauth: dict[str, Any] = {"connected": False, "reason": "no session", "path": str(garth_dir)}
    if garth_dir.is_dir() and garmin_resume(user_ctx):
        token = garth.client.oauth2_token
        oauth = {
            "connected": True,
            "path": str(garth_dir),
            "token_expires_at": getattr(token, "expires_at", None),
        }

    web = web_status(user_ctx)
    connected = oauth.get("connected") or web.get("connected")
    return {
        "connected": connected,
        "tenant_user_id": user_ctx.user_id,
        "oauth": oauth,
        "web": web,
        "upload_ready": web.get("connected", False),
    }


def upload_fit(
    fit_bytes: bytes,
    filename: str,
    ctx: UserContext | None = None,
) -> dict[str, Any]:
    user_ctx = as_context(ctx)
    settings = user_ctx.settings
    ensure_web_session(user_ctx)

    if not web_resume(user_ctx) and settings.garmin_email and settings.garmin_password:
        logger.info("Garmin web session missing or expired — re-login")
        web_login(settings.garmin_email, settings.garmin_password, user_ctx)

    if web_resume(user_ctx):
        try:
            return upload_fit_via_browser(fit_bytes, filename, user_ctx)
        except Exception as exc:
            logger.warning("Garmin browser upload failed, trying HTTP: %s", exc)
        try:
            return upload_fit_via_web(fit_bytes, filename, user_ctx)
        except Exception as exc:
            logger.warning("Garmin web upload failed, trying OAuth: %s", exc)

    garth_dir = _garth_dir(user_ctx)
    if not garmin_resume(user_ctx):
        raise RuntimeError(
            f"Garmin session not available for {user_ctx.user_id} — "
            f"run: getsync --user {user_ctx.user_id} garmin login"
        )
    buf = io.BytesIO(fit_bytes)
    buf.name = filename if filename.endswith(".fit") else f"{filename}.fit"
    result = garth.upload(buf)
    garth.save(str(garth_dir))
    return result
