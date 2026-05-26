"""Garmin Connect web session (JWT_WEB) for FIT upload via modern proxy.

connectapi.garmin.com/upload-service/upload is blocked by Cloudflare for
programmatic OAuth/DI clients. The web UI proxy accepts uploads when
authenticated with JWT_WEB cookies from a browser-like SSO flow.
"""

from __future__ import annotations

import base64
import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Any

import httpx

from getsync.config import Settings, get_settings
from getsync.users.context import UserContext, as_context

logger = logging.getLogger("getsync.garmin.web")

SESSION_FILE = "session.json"
WIDGET_DELAY_MIN_S = 3.0
WIDGET_DELAY_MAX_S = 8.0
UPLOAD_URL = "https://connect.garmin.com/modern/proxy/upload-service/upload/.fit"
PROFILE_URL = "https://connect.garmin.com/modern/currentuser-service/user/info"


def _web_dir(ctx: UserContext | Settings | None = None) -> Path:
    if isinstance(ctx, UserContext):
        return ctx.garmin_web_dir
    settings = ctx or get_settings()
    return settings.data_dir / "garmin_web"


def _session_path(ctx: UserContext | Settings | None = None) -> Path:
    return _web_dir(ctx) / SESSION_FILE


def _jwt_expires_at(jwt_web: str) -> float | None:
    try:
        payload_b64 = jwt_web.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        exp = payload.get("exp")
        return float(exp) if exp else None
    except Exception:
        return None


def _save_session(
    cookies: dict[str, str],
    ctx: UserContext | None = None,
    *,
    refresh_method: str | None = None,
    refreshed: bool = False,
) -> None:
    user_ctx = as_context(ctx)
    web_dir = _web_dir(user_ctx)
    web_dir.mkdir(parents=True, exist_ok=True)
    jwt_web = cookies.get("JWT_WEB", "")
    prev = _load_session(user_ctx) or {}
    data = {
        "cookies": cookies,
        "jwt_web": jwt_web,
        "expires_at": _jwt_expires_at(jwt_web),
        "saved_at": time.time(),
        "refreshed_at": time.time() if refreshed else prev.get("refreshed_at"),
        "refresh_method": refresh_method or prev.get("refresh_method"),
    }
    _session_path(user_ctx).write_text(json.dumps(data, indent=2))


def _load_session(ctx: UserContext | None = None) -> dict[str, Any] | None:
    path = _session_path(ctx)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _client_from_cookies(cookies: dict[str, str]) -> httpx.Client:
    return httpx.Client(
        cookies=cookies,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        },
        timeout=120.0,
        follow_redirects=True,
    )


def _jwt_valid(jwt_web: str | None) -> bool:
    if not jwt_web or jwt_web.count(".") != 2:
        return False
    exp = _jwt_expires_at(jwt_web)
    return not (exp and time.time() > exp - 60)


def _api_headers(csrf_token: str | None = None) -> dict[str, str]:
    headers = {
        "Accept": "application/json, text/plain, */*",
        "NK": "NT",
        "Origin": "https://connect.garmin.com",
        "Referer": "https://connect.garmin.com/modern/import-data",
        "DI-Backend": "connectapi.garmin.com",
        "X-Requested-With": "XMLHttpRequest",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }
    if csrf_token:
        headers["connect-csrf-token"] = csrf_token
    return headers


def _has_session_cookie(cookies: dict[str, str]) -> bool:
    return bool(cookies.get("session") or cookies.get("SESSION"))


def _fetch_csrf(client: httpx.Client) -> str | None:
    resp = client.get("https://connect.garmin.com/modern/")
    resp.raise_for_status()
    match = re.search(r'name="csrf-token"\s+content="([^"]+)"', resp.text)
    return match.group(1) if match else None


def _live_check_session(cookies: dict[str, str]) -> bool:
    try:
        with _client_from_cookies(cookies) as client:
            resp = client.get(PROFILE_URL, headers=_api_headers())
            if resp.status_code != 200:
                return False
            if "json" not in (resp.headers.get("content-type") or ""):
                return False
            data = resp.json()
            return bool(data.get("username") or data.get("userProfileId"))
    except Exception:
        return False


def _validate_session(cookies: dict[str, str]) -> bool:
    if not _jwt_valid(cookies.get("JWT_WEB")):
        return False
    if _has_session_cookie(cookies):
        return True
    return _live_check_session(cookies)


def import_web_cookies(cookies: dict[str, str], ctx: UserContext | None = None) -> None:
    """Save browser cookies for web upload."""
    cleaned = {k: v for k, v in cookies.items() if v}
    if not _jwt_valid(cleaned.get("JWT_WEB")):
        raise RuntimeError("JWT_WEB missing, invalid, or expired")
    _save_session(cleaned, ctx)


def _widget_login(email: str, password: str) -> dict[str, str]:
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError as exc:
        raise RuntimeError("curl_cffi is required for Garmin web login") from exc

    domain = "garmin.com"
    sso = f"https://sso.{domain}"
    connect = f"https://connect.{domain}"
    sso_base = f"{sso}/sso"
    sso_embed = f"{sso_base}/embed"
    embed_params = {
        "id": "gauth-widget",
        "embedWidget": "true",
        "gauthHost": sso_base,
    }
    signin_params = {
        **embed_params,
        "gauthHost": sso_embed,
        "service": sso_embed,
        "source": sso_embed,
        "redirectAfterAccountLoginUrl": sso_embed,
        "redirectAfterAccountCreationUrl": sso_embed,
    }

    sess = cffi_requests.Session(impersonate="chrome", timeout=30)
    resp = sess.get(sso_embed, params=embed_params)
    resp.raise_for_status()

    resp = sess.get(
        f"{sso_base}/signin",
        params=signin_params,
        headers={"Referer": sso_embed},
    )
    resp.raise_for_status()
    csrf_match = re.search(r'name="_csrf"\s+value="(.+?)"', resp.text)
    if not csrf_match:
        raise RuntimeError("Garmin SSO: missing CSRF token")

    delay = random.uniform(WIDGET_DELAY_MIN_S, WIDGET_DELAY_MAX_S)
    logger.debug("Garmin web login: waiting %.0fs", delay)
    time.sleep(delay)

    resp = sess.post(
        f"{sso_base}/signin",
        params=signin_params,
        headers={"Referer": resp.url},
        data={
            "username": email,
            "password": password,
            "embed": "true",
            "_csrf": csrf_match.group(1),
        },
    )
    title_match = re.search(r"<title>(.+?)</title>", resp.text)
    title = title_match.group(1) if title_match else ""
    if "MFA" in title or "Authentication Application" in title:
        raise RuntimeError("Garmin MFA required — complete login in browser, then retry")
    if title != "Success":
        raise RuntimeError(f"Garmin web login failed: {title or resp.status_code}")

    ticket_match = re.search(r'embed\?ticket=([^"]+)"', resp.text)
    if not ticket_match:
        raise RuntimeError("Garmin web login: missing service ticket")

    sess.get(
        f"{connect}/app/activities",
        params={"ticket": ticket_match.group(1)},
        allow_redirects=True,
    )
    cookies = sess.cookies.get_dict()
    if not cookies.get("JWT_WEB"):
        raise RuntimeError("Garmin web login: JWT_WEB cookie not set")
    return cookies


def web_login(email: str, password: str, ctx: UserContext | None = None) -> None:
    """Browser-like SSO login; stores JWT_WEB cookies for web upload."""
    cookies = _widget_login(email, password)
    _save_session(cookies, ctx)
    logger.info("Garmin web session saved (%d cookies)", len(cookies))


def web_resume(
    ctx: UserContext | None = None,
    *,
    auto_refresh: bool = True,
) -> dict[str, str] | None:
    """Load stored web session cookies if still valid."""
    user_ctx = as_context(ctx)
    stored = _load_session(user_ctx)
    if not stored:
        return None
    cookies = stored.get("cookies") or {}
    if _validate_session(cookies):
        return cookies
    if auto_refresh and _has_session_cookie(cookies):
        from getsync.garmin.web_refresh import refresh_web_session

        refresh_web_session(user_ctx, trigger="auto")
        stored = _load_session(user_ctx)
        if stored:
            cookies = stored.get("cookies") or {}
            if _validate_session(cookies):
                return cookies
    return None


def web_status(ctx: UserContext | None = None) -> dict[str, Any]:
    user_ctx = as_context(ctx)
    path = _session_path(user_ctx)
    stored = _load_session(user_ctx)
    if not stored:
        return {"connected": False, "reason": "no session", "path": str(path)}

    cookies = stored.get("cookies") or {}
    jwt_web = cookies.get("JWT_WEB") or stored.get("jwt_web")
    expires_at = stored.get("expires_at") or (
        _jwt_expires_at(jwt_web) if jwt_web else None
    )
    valid = _validate_session(cookies) if cookies else False
    return {
        "connected": valid,
        "reason": None if valid else "invalid or expired session",
        "path": str(path),
        "expires_at": expires_at,
        "refreshed_at": stored.get("refreshed_at"),
        "refresh_method": stored.get("refresh_method"),
    }


def _parse_upload_response(resp: httpx.Response) -> dict[str, Any]:
    content_type = resp.headers.get("content-type") or ""
    if "json" not in content_type:
        snippet = resp.text[:200].replace("\n", " ")
        raise RuntimeError(
            f"Garmin web upload returned non-JSON ({resp.status_code}): {snippet}"
        )

    payload = resp.json()
    result = payload.get("detailedImportResult", payload)

    successes = result.get("successes") or []
    if successes:
        return {"status": "uploaded", "detailedImportResult": result}

    failures = result.get("failures") or []
    if failures:
        messages = failures[0].get("messages") or []
        if messages and messages[0].get("code") == 202:
            return {
                "status": "duplicate",
                "detailedImportResult": result,
                "activity_id": failures[0].get("internalId"),
            }
        msg = messages[0].get("content") if messages else str(failures[0])
        raise RuntimeError(f"Garmin upload rejected: {msg}")

    if resp.status_code in (200, 201, 409):
        return {"status": "uploaded", "detailedImportResult": result}

    raise RuntimeError(f"Garmin upload failed: HTTP {resp.status_code}")


def upload_fit_via_web(
    fit_bytes: bytes,
    filename: str,
    ctx: UserContext | None = None,
) -> dict[str, Any]:
    """Upload FIT through connect.garmin.com modern proxy (JWT_WEB session)."""
    user_ctx = as_context(ctx)
    cookies = web_resume(user_ctx)
    if not cookies:
        raise RuntimeError(
            f"Garmin web session not available for {user_ctx.user_id} — "
            f"run: getsync --user {user_ctx.user_id} garmin web-login"
        )

    jwt_web = cookies.get("JWT_WEB")
    if not jwt_web:
        raise RuntimeError(
            "Garmin web session not available — run: getsync garmin web-login"
        )
    safe_name = filename if filename.endswith(".fit") else f"{filename}.fit"

    with _client_from_cookies(cookies) as client:
        csrf = _fetch_csrf(client)
        headers = _api_headers(csrf)
        resp = client.post(
            UPLOAD_URL,
            headers=headers,
            files={"file": (safe_name, fit_bytes, "application/octet-stream")},
        )

    if resp.status_code >= 400 and "json" not in (resp.headers.get("content-type") or ""):
        resp.raise_for_status()

    return _parse_upload_response(resp)
