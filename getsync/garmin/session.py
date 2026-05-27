import io
import logging
from pathlib import Path
from typing import Any

import garth

from getsync.users.context import UserContext, as_context
from getsync.garmin.browser_upload import upload_fit_via_browser
from getsync.garmin.web_session import (
    upload_fit_via_web,
    web_login,
    web_resume,
    web_status,
)

logger = logging.getLogger("getsync.garmin")


def _garth_dir(ctx: UserContext | None = None) -> Path:
    return as_context(ctx).garth_dir


def garmin_login(
    email: str,
    password: str,
    ctx: UserContext | None = None,
    *,
    save_credentials: bool = True,
    store_password: bool = True,
) -> None:
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
    if save_credentials:
        from getsync.credentials.garmin import save_garmin_login
        from getsync.credentials.store import CredentialStoreError

        try:
            save_garmin_login(
                user_ctx,
                email,
                password if store_password else None,
                store_password=store_password,
            )
        except CredentialStoreError as exc:
            logger.warning(
                "Garmin sessions saved but encrypted credentials not stored for %s: %s",
                user_ctx.user_id,
                exc,
            )


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
    from getsync.credentials.garmin import garmin_auto_login_configured

    return {
        "connected": connected,
        "tenant_user_id": user_ctx.user_id,
        "oauth": oauth,
        "web": web,
        "upload_ready": web.get("connected", False),
        "auto_login_configured": garmin_auto_login_configured(user_ctx),
    }


def upload_fit(
    fit_bytes: bytes,
    filename: str,
    ctx: UserContext | None = None,
) -> dict[str, Any]:
    user_ctx = as_context(ctx)
    from getsync.garmin.ensure import ensure_garmin_web_session

    ensure_garmin_web_session(user_ctx, trigger="upload")

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
        from getsync.garmin.ensure import try_garmin_auto_login

        if not try_garmin_auto_login(user_ctx) or not garmin_resume(user_ctx):
            raise RuntimeError(
                f"Garmin session not available for {user_ctx.user_id} — "
                f"run: getsync --user {user_ctx.user_id} garmin login --save-credentials"
            )
    from getsync.garmin.upload_errors import (
        garmin_duplicate_result,
        is_garmin_duplicate_upload,
    )

    buf = io.BytesIO(fit_bytes)
    buf.name = filename if filename.endswith(".fit") else f"{filename}.fit"
    try:
        result = garth.upload(buf)
    except Exception as exc:
        if is_garmin_duplicate_upload(exc):
            garth.save(str(garth_dir))
            return garmin_duplicate_result()
        raise
    garth.save(str(garth_dir))
    return result
