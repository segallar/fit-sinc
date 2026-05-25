import io
import logging
from pathlib import Path
from typing import Any

import garth

from fit_sinc.config import Settings, get_settings
from fit_sinc.garmin.browser_upload import upload_fit_via_browser
from fit_sinc.garmin.web_session import (
    upload_fit_via_web,
    web_login,
    web_resume,
    web_status,
)
from fit_sinc.garmin.web_refresh import ensure_web_session

logger = logging.getLogger("fit_sinc.garmin")


def _garth_dir(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.garth_dir


def garmin_login(email: str, password: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    garth_dir = _garth_dir(settings)
    garth_dir.mkdir(parents=True, exist_ok=True)
    try:
        garth.login(email, password)
        garth.save(str(garth_dir))
    except Exception as exc:
        if garmin_resume(settings):
            logger.warning("Garmin OAuth login failed, keeping existing session: %s", exc)
        else:
            raise
    web_login(email, password, settings)


def garmin_resume(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    garth_dir = _garth_dir(settings)
    if not garth_dir.is_dir():
        return False
    try:
        garth.resume(str(garth_dir))
        return garth.client.oauth2_token is not None
    except Exception:
        return False


def garmin_status(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    garth_dir = _garth_dir(settings)
    oauth: dict[str, Any] = {"connected": False, "reason": "no session", "path": str(garth_dir)}
    if garth_dir.is_dir() and garmin_resume(settings):
        token = garth.client.oauth2_token
        oauth = {
            "connected": True,
            "path": str(garth_dir),
            "token_expires_at": getattr(token, "expires_at", None),
        }

    web = web_status(settings)
    connected = oauth.get("connected") or web.get("connected")
    return {
        "connected": connected,
        "oauth": oauth,
        "web": web,
        "upload_ready": web.get("connected", False),
    }


def upload_fit(
    fit_bytes: bytes,
    filename: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    ensure_web_session(settings)

    if not web_resume(settings) and settings.garmin_email and settings.garmin_password:
        logger.info("Garmin web session missing or expired — re-login")
        web_login(settings.garmin_email, settings.garmin_password, settings)

    if web_resume(settings):
        try:
            return upload_fit_via_browser(fit_bytes, filename, settings)
        except Exception as exc:
            logger.warning("Garmin browser upload failed, trying HTTP: %s", exc)
        try:
            return upload_fit_via_web(fit_bytes, filename, settings)
        except Exception as exc:
            logger.warning("Garmin web upload failed, trying OAuth: %s", exc)

    garth_dir = _garth_dir(settings)
    if not garmin_resume(settings):
        raise RuntimeError("Garmin session not available — run: fit_sinc garmin login")
    buf = io.BytesIO(fit_bytes)
    buf.name = filename if filename.endswith(".fit") else f"{filename}.fit"
    result = garth.upload(buf)
    garth.save(str(garth_dir))
    return result
