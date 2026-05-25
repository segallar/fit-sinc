"""Automatic JWT_WEB refresh for Garmin Connect web upload sessions."""

from __future__ import annotations

import logging
import time
from typing import Any

from fit_sinc.config import Settings, get_settings
from fit_sinc.timeutil import format_ts
from fit_sinc.garmin.web_session import (
    _has_session_cookie,
    _jwt_expires_at,
    _jwt_valid,
    _load_session,
    _save_session,
    _validate_session,
)

logger = logging.getLogger("fit_sinc.garmin.web_refresh")

REFRESH_URL = "https://connect.garmin.com/modern/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def jwt_needs_refresh(
    jwt_web: str | None,
    *,
    before_sec: int,
) -> bool:
    if not jwt_web:
        return True
    if not _jwt_valid(jwt_web):
        return True
    exp = _jwt_expires_at(jwt_web)
    if exp is None:
        return True
    return time.time() >= exp - before_sec


def _session_cookie(cookies: dict[str, str]) -> str | None:
    return cookies.get("session") or cookies.get("SESSION")


def _collect_garmin_cookies(jar: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    for cookie in jar:
        domain = getattr(cookie, "domain", "") or ""
        if "garmin.com" not in domain:
            continue
        out[cookie.name] = cookie.value
    return out


def _log_refresh(trigger: str, event_type: str, message: str = "") -> None:
    try:
        from fit_sinc.state.store import Store

        Store(get_settings().db_path).log_session_refresh(trigger, event_type, message)
    except Exception:
        logger.debug("session refresh log write failed", exc_info=True)


def session_monitor(settings: Settings | None = None) -> dict[str, Any]:
    """Current Garmin web session state for monitoring UI."""
    settings = settings or get_settings()
    stored = _load_session(settings) or {}
    cookies = stored.get("cookies") or {}
    jwt_web = cookies.get("JWT_WEB")
    expires_at = stored.get("expires_at") or (
        _jwt_expires_at(jwt_web) if jwt_web else None
    )
    now = time.time()
    ttl_sec: float | None = None
    if expires_at:
        ttl_sec = max(0.0, float(expires_at) - now)

    return {
        "upload_ready": _validate_session(cookies) if cookies else False,
        "has_session_cookie": _has_session_cookie(cookies),
        "jwt_valid": _jwt_valid(jwt_web),
        "needs_refresh": jwt_needs_refresh(
            jwt_web, before_sec=settings.garmin_jwt_refresh_before_sec
        ),
        "expires_at": expires_at,
        "ttl_sec": ttl_sec,
        "refreshed_at": stored.get("refreshed_at"),
        "refresh_method": stored.get("refresh_method"),
        "refresh_interval_sec": settings.garmin_jwt_refresh_interval_sec,
        "refresh_before_sec": settings.garmin_jwt_refresh_before_sec,
        "session_path": str(settings.data_dir / "garmin_web" / "session.json"),
    }


def refresh_via_http(existing: dict[str, str]) -> dict[str, str] | None:
    """Refresh JWT_WEB using the long-lived `session` cookie (no Playwright)."""
    session = _session_cookie(existing)
    if not session:
        return None

    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        logger.warning("curl_cffi unavailable — skip HTTP JWT refresh")
        return None

    sess = cffi_requests.Session(impersonate="chrome", timeout=30)
    for domain in ("connect.garmin.com", ".garmin.com"):
        sess.cookies.set("session", session, domain=domain)

    resp = sess.get(
        REFRESH_URL,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        allow_redirects=True,
    )
    final_url = str(resp.url).lower()
    if resp.status_code >= 400 or "sign-in" in final_url or "signin" in final_url:
        logger.warning(
            "Garmin HTTP JWT refresh failed: HTTP %s url=%s",
            resp.status_code,
            resp.url,
        )
        return None

    refreshed = _collect_garmin_cookies(sess.cookies.jar)
    merged = {**existing, **refreshed}
    if not _jwt_valid(merged.get("JWT_WEB")):
        logger.warning("Garmin HTTP JWT refresh did not yield a valid JWT_WEB")
        return None
    return merged


def refresh_web_session(
    settings: Settings | None = None,
    *,
    force: bool = False,
    trigger: str = "auto",
) -> dict[str, Any]:
    """Refresh JWT_WEB if expiring soon. Requires `session` cookie from browser import."""
    settings = settings or get_settings()
    stored = _load_session(settings)
    if not stored:
        result = {"refreshed": False, "reason": "no session file"}
        _log_refresh(trigger, "failed", result["reason"])
        return result

    cookies = dict(stored.get("cookies") or {})
    if not cookies:
        result = {"refreshed": False, "reason": "empty cookies"}
        _log_refresh(trigger, "failed", result["reason"])
        return result

    before_sec = settings.garmin_jwt_refresh_before_sec
    jwt_web = cookies.get("JWT_WEB")
    if not force and not jwt_needs_refresh(jwt_web, before_sec=before_sec):
        result = {
            "refreshed": False,
            "reason": "jwt still valid",
            "expires_at": _jwt_expires_at(jwt_web),
        }
        if trigger != "background":
            _log_refresh(trigger, "ok", result["reason"])
        else:
            exp = _jwt_expires_at(jwt_web)
            _log_refresh(
                trigger,
                "ok",
                f"jwt valid until {format_ts(exp)}",
            )
        return result

    if not _has_session_cookie(cookies):
        result = {"refreshed": False, "reason": "no session cookie — import from browser"}
        _log_refresh(trigger, "failed", result["reason"])
        return result

    method: str | None = None
    updated: dict[str, str] | None = refresh_via_http(cookies)
    if updated:
        method = "http"
    else:
        from fit_sinc.garmin.browser_upload import refresh_cookies_via_browser

        updated = refresh_cookies_via_browser(cookies)
        if updated:
            method = "playwright"

    if not updated:
        if settings.garmin_email and settings.garmin_password:
            from fit_sinc.garmin.web_session import web_login

            try:
                web_login(settings.garmin_email, settings.garmin_password, settings)
                method = "login"
                stored = _load_session(settings)
                cookies = dict(stored.get("cookies") or {}) if stored else {}
                if _jwt_valid(cookies.get("JWT_WEB")):
                    exp = _jwt_expires_at(cookies.get("JWT_WEB"))
                    msg = f"via {method}, expires {format_ts(exp)}"
                    _log_refresh(trigger, "refreshed", msg)
                    return {
                        "refreshed": True,
                        "method": method,
                        "expires_at": exp,
                    }
            except Exception as exc:
                logger.warning("Garmin web login refresh failed: %s", exc)
                _log_refresh(trigger, "failed", f"web login: {exc}")
        result = {"refreshed": False, "reason": "refresh failed — re-import browser cookies"}
        _log_refresh(trigger, "failed", result["reason"])
        return result

    _save_session(updated, settings, refresh_method=method, refreshed=True)
    new_jwt = updated.get("JWT_WEB")
    exp = _jwt_expires_at(new_jwt)
    logger.info("Garmin JWT refreshed via %s (expires %s)", method, exp)
    _log_refresh(trigger, "refreshed", f"via {method}, expires {format_ts(exp)}")
    return {
        "refreshed": True,
        "method": method,
        "expires_at": exp,
    }


def ensure_web_session(
    settings: Settings | None = None,
    *,
    trigger: str = "upload",
) -> bool:
    """Refresh JWT if needed; return True when upload session is ready."""
    settings = settings or get_settings()
    refresh_web_session(settings, trigger=trigger)
    stored = _load_session(settings)
    if not stored:
        return False
    cookies = stored.get("cookies") or {}
    return _validate_session(cookies)
