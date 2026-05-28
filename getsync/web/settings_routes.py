"""User settings: profile, password, Hammerhead/Garmin connections."""

from __future__ import annotations

import asyncio
import logging
import shutil

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from getsync.audit import log as audit_log
from getsync.audit import request_ip
from getsync.config import get_settings
from getsync.garmin.session import garmin_login
from getsync.garmin.web_refresh import refresh_web_session
from getsync.hammerhead.oauth import HammerheadOAuth
from getsync.providers.strava.client import StravaClient
from getsync.providers.strava.oauth import StravaOAuth
from getsync.state.store import Store
from getsync.storage import save_json
from getsync.users.context import UserContext
from getsync.users.locale import normalize_locale
from getsync.web import html as H
from getsync.web.app_i18n import cabinet_strings, flash_message
from getsync.web.auth import user_context_from_session
from getsync.web.cabinet import render_cabinet
from getsync.web.connections import (
    connection_settings_view,
    garmin_session_context,
    list_connections,
)
from getsync.web.oauth_state import (
    sign_hammerhead_oauth_state,
    sign_strava_oauth_state,
    verify_hammerhead_oauth_state,
    verify_strava_oauth_state,
)
from getsync.web.site_i18n import LANG_COOKIE

router = APIRouter(prefix="/app/settings", tags=["settings"])
P = "/app/settings"
logger = logging.getLogger("getsync.web.settings")


def _store() -> Store:
    return Store(get_settings().db_path)


def _ctx(request: Request) -> UserContext:
    ctx = user_context_from_session(request)
    if not ctx:
        raise HTTPException(status_code=401)
    return ctx


SETTINGS_BASE_SECTIONS = frozenset({"profile", "password"})
SETTINGS_CONNECTION_SECTIONS = frozenset({"hammerhead", "garmin", "strava", "wahoo"})
SETTINGS_SECTIONS = SETTINGS_BASE_SECTIONS | SETTINGS_CONNECTION_SECTIONS


def _settings_section(request: Request) -> str:
    raw = request.query_params.get("section", "profile").strip().lower()
    if raw == "connections":
        return "hammerhead"
    if raw in SETTINGS_SECTIONS:
        return raw
    return "profile"


def _settings_nav_connections(groups) -> list[dict[str, object]]:
    return [
        {"id": c.id, "name": c.name, "available": c.available}
        for c in (*groups.sources, *groups.sinks)
    ]


def _settings_connections_open(section: str) -> bool:
    return section in SETTINGS_CONNECTION_SECTIONS


def _active_connection(groups, section: str):
    if section not in SETTINGS_CONNECTION_SECTIONS:
        return None
    for c in (*groups.sources, *groups.sinks):
        if c.id == section:
            return c
    return None


def _redirect(
    msg: str = "",
    *,
    error: str = "",
    section: str = "",
    anchor: str = "",
) -> RedirectResponse:
    params: dict[str, str] = {}
    if msg:
        params["msg"] = msg
    if error:
        params["error"] = error
    sec = section.strip().lower()
    if not sec and anchor.startswith("garmin"):
        sec = "garmin"
    if sec == "connections":
        sec = "hammerhead"
    if sec in SETTINGS_SECTIONS:
        params["section"] = sec
    q = H.query_string(params)
    url = f"{P}?{q}" if q else P
    if anchor:
        url = f"{url}#{anchor}"
    return RedirectResponse(url, status_code=303)


def _flash_from_query(request: Request, lang: str) -> dict[str, str]:
    t = cabinet_strings(lang)
    flash: dict[str, str] = {}
    msg = request.query_params.get("msg", "").strip()
    err = request.query_params.get("error", "").strip()
    if msg:
        text = flash_message(lang, msg)
        if text:
            flash["ok"] = text
    if err == "hh_not_configured":
        flash["error"] = "Hammerhead OAuth is not configured on the server."
    elif err == "hh_state":
        flash["error"] = "Hammerhead OAuth state invalid or expired."
    elif err == "hh_user_mismatch":
        flash["error"] = "Hammerhead OAuth user mismatch."
    elif err.startswith("hh_"):
        flash["error"] = f"Hammerhead OAuth error: {err[3:]}"
    elif err == "strava_not_configured":
        flash["error"] = t["flash_strava_not_configured"]
    elif err == "strava_state":
        flash["error"] = t["flash_strava_state"]
    elif err == "strava_user_mismatch":
        flash["error"] = t["flash_strava_user_mismatch"]
    elif err.startswith("strava_"):
        flash["error"] = f"Strava OAuth error: {err[7:]}"
    elif err == "password_too_short":
        flash["error"] = "New password must be at least 8 characters."
    elif err == "password_mismatch":
        flash["error"] = "New passwords do not match."
    elif err == "wrong_current_password":
        flash["error"] = "Current password is incorrect."
    elif err == "garmin_credentials_required":
        flash["error"] = t["flash_garmin_credentials_required"]
    elif err == "garmin_login_failed":
        flash["error"] = t["flash_garmin_login_failed"]
    elif err:
        flash["error"] = err.replace("_", " ")
    return flash


def _hammerhead_oauth(request: Request) -> HammerheadOAuth:
    settings = get_settings()
    redirect = settings.hammerhead_web_redirect_uri.strip()
    if not redirect:
        base = str(request.base_url).rstrip("/")
        redirect = f"{base}{P}/hammerhead/callback"
    return HammerheadOAuth(
        client_id=settings.hammerhead_client_id,
        client_secret=settings.hammerhead_client_secret,
        redirect_uri=redirect,
        scope=settings.hammerhead_scope,
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def settings_page(request: Request) -> str:
    ctx = _ctx(request)
    user = _store().get_user(ctx.user_id)
    if not user:
        raise HTTPException(status_code=404)
    connection_groups = list_connections(ctx, user)
    section = _settings_section(request)
    return render_cabinet(
        request,
        "pages/app/settings.html",
        active=f"{P}/",
        user=user,
        flash=_flash_from_query(request, user.locale),
        conn=connection_settings_view(ctx, user),
        connection_groups=connection_groups,
        settings_section=section,
        settings_connections_open=_settings_connections_open(section),
        settings_nav_connections=_settings_nav_connections(connection_groups),
        active_connection=_active_connection(connection_groups, section),
        **garmin_session_context(ctx),
    )


@router.post("/profile", include_in_schema=False)
async def settings_profile(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(...),
    telegram: str = Form(""),
    timezone: str = Form("Europe/Moscow"),
    locale: str = Form("en"),
) -> RedirectResponse:
    ctx = _ctx(request)
    store = _store()
    loc = normalize_locale(locale)
    try:
        store.update_user(
            ctx.user_id,
            display_name=display_name.strip(),
            email=email.strip(),
            telegram=telegram.strip() or None,
            timezone=timezone,
            locale=loc,
        )
    except Exception as exc:
        return _redirect(error=str(exc), section="profile")
    user = store.get_user(ctx.user_id)
    audit_log(
        store,
        "settings_profile",
        f"locale={loc} timezone={timezone.strip()} ip={request_ip(request)}",
        user_id=ctx.user_id,
        subject=user.slug if user else ctx.user_id,
    )
    response = _redirect("profile_saved", section="profile")
    response.set_cookie(
        LANG_COOKIE,
        loc,
        max_age=365 * 24 * 3600,
        httponly=False,
        samesite="lax",
    )
    return response


@router.post("/password", include_in_schema=False)
async def settings_password(
    request: Request,
    current_password: str = Form(""),
    new_password: str = Form(""),
    new_password_confirm: str = Form(""),
) -> RedirectResponse:
    ctx = _ctx(request)
    user = _store().get_user(ctx.user_id)
    if not user:
        raise HTTPException(status_code=404)
    if len(new_password) < 8:
        return _redirect(error="password_too_short", section="password")
    if new_password != new_password_confirm:
        return _redirect(error="password_mismatch", section="password")
    if not _store().verify_user_password(user.email, current_password):
        return _redirect(error="wrong_current_password", section="password")
    store = _store()
    store.update_user(ctx.user_id, password=new_password)
    audit_log(
        store,
        "settings_password",
        f"ip={request_ip(request)}",
        user_id=ctx.user_id,
        subject=user.slug,
    )
    return _redirect("password_changed", section="password")


def _strava_oauth(request: Request) -> StravaOAuth:
    settings = get_settings()
    redirect = settings.strava_web_redirect_uri.strip()
    if not redirect:
        base = str(request.base_url).rstrip("/")
        redirect = f"{base}{P}/strava/callback"
    scope = settings.strava_scope.strip() or "read,activity:read,activity:read_all,activity:write"
    return StravaOAuth(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
        redirect_uri=redirect,
        scope=scope,
    )


@router.get("/hammerhead/connect", include_in_schema=False)
async def hammerhead_connect(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    settings = get_settings()
    if not settings.hammerhead_client_id or not settings.hammerhead_client_secret:
        return _redirect(error="hh_not_configured", section="hammerhead")
    oauth = _hammerhead_oauth(request)
    state = sign_hammerhead_oauth_state(ctx.user_id, settings.session_secret)
    url, _ = oauth.build_authorize_url(state=state)
    return RedirectResponse(url, status_code=303)


@router.get("/hammerhead/callback", include_in_schema=False)
async def hammerhead_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
) -> RedirectResponse:
    if error:
        return _redirect(error=f"hh_{error}", section="hammerhead")
    uid = verify_hammerhead_oauth_state(state, get_settings().session_secret)
    if not uid:
        return _redirect(error="hh_state", section="hammerhead")
    session_ctx = user_context_from_session(request)
    if session_ctx and session_ctx.user_id != uid:
        return _redirect(error="hh_user_mismatch", section="hammerhead")
    if not session_ctx:
        from getsync.web.auth import login_user

        login_user(request, uid)
        actor = _store().get_user(uid)
        audit_log(
            _store(),
            "user_login",
            f"via=hammerhead_oauth ip={request_ip(request)}",
            user_id=uid,
            subject=actor.slug if actor else uid,
        )
    if not code:
        return _redirect(error="hh_missing_code", section="hammerhead")
    oauth = _hammerhead_oauth(request)
    try:
        tokens = await oauth.exchange_code(code)
    except Exception as exc:
        return _redirect(error=str(exc), section="hammerhead")
    ctx = UserContext(uid, get_settings())
    save_json(ctx.hammerhead_tokens_path, tokens.to_dict())
    hh_uid = tokens.user_id or None
    store = _store()
    if hh_uid:
        store.update_user(uid, hammerhead_user_id=str(hh_uid))
    target = store.get_user(uid)
    audit_log(
        store,
        "settings_hammerhead_connected",
        f"hammerhead_user_id={hh_uid or '—'} ip={request_ip(request)}",
        user_id=uid,
        subject=target.slug if target else uid,
    )
    return _redirect("hh_connected", section="hammerhead")


@router.post("/hammerhead/disconnect", include_in_schema=False)
async def hammerhead_disconnect(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    path = ctx.hammerhead_tokens_path
    if path.is_file():
        path.unlink()
    user = _store().get_user(ctx.user_id)
    audit_log(
        _store(),
        "settings_hammerhead_disconnected",
        f"ip={request_ip(request)}",
        user_id=ctx.user_id,
        subject=user.slug if user else ctx.user_id,
    )
    return _redirect("hh_disconnected", section="hammerhead")


@router.get("/strava/connect", include_in_schema=False)
async def strava_connect(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    settings = get_settings()
    if not settings.strava_client_id or not settings.strava_client_secret:
        return _redirect(error="strava_not_configured", section="strava")
    oauth = _strava_oauth(request)
    state = sign_strava_oauth_state(ctx.user_id, settings.session_secret)
    url, _ = oauth.build_authorize_url(state=state)
    return RedirectResponse(url, status_code=303)


@router.get("/strava/callback", include_in_schema=False)
async def strava_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
) -> RedirectResponse:
    if error:
        return _redirect(error=f"strava_{error}", section="strava")
    uid = verify_strava_oauth_state(state, get_settings().session_secret)
    if not uid:
        return _redirect(error="strava_state", section="strava")
    session_ctx = user_context_from_session(request)
    if session_ctx and session_ctx.user_id != uid:
        return _redirect(error="strava_user_mismatch", section="strava")
    if not session_ctx:
        from getsync.web.auth import login_user

        login_user(request, uid)
        actor = _store().get_user(uid)
        audit_log(
            _store(),
            "user_login",
            f"via=strava_oauth ip={request_ip(request)}",
            user_id=uid,
            subject=actor.slug if actor else uid,
        )
    if not code:
        return _redirect(error="strava_missing_code", section="strava")
    oauth = _strava_oauth(request)
    try:
        tokens = await oauth.exchange_code(code)
    except Exception as exc:
        logger.warning("Strava OAuth exchange failed for %s: %s", uid, exc)
        return _redirect(error="strava_exchange_failed", section="strava")
    ctx = UserContext(uid, get_settings())
    StravaClient(ctx).save_tokens(tokens)
    target = _store().get_user(uid)
    audit_log(
        _store(),
        "settings_strava_connected",
        f"athlete_id={tokens.athlete_id or '—'} ip={request_ip(request)}",
        user_id=uid,
        subject=target.slug if target else uid,
    )
    return _redirect("strava_connected", section="strava")


@router.post("/strava/disconnect", include_in_schema=False)
async def strava_disconnect(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    client = StravaClient(ctx)
    tokens = client.load_tokens()
    if tokens:
        oauth = _strava_oauth(request)
        try:
            await oauth.deauthorize(tokens.access_token)
        except Exception as exc:
            logger.warning("Strava deauthorize failed for %s: %s", ctx.user_id, exc)
    client.clear_tokens()
    user = _store().get_user(ctx.user_id)
    audit_log(
        _store(),
        "settings_strava_disconnected",
        f"ip={request_ip(request)}",
        user_id=ctx.user_id,
        subject=user.slug if user else ctx.user_id,
    )
    return _redirect("strava_disconnected", section="strava")


@router.post("/garmin/login", include_in_schema=False)
async def garmin_login_settings(
    request: Request,
    garmin_email: str = Form(""),
    garmin_password: str = Form(""),
    save_credentials: str = Form(""),
) -> RedirectResponse:
    ctx = _ctx(request)
    email = garmin_email.strip()
    password = garmin_password
    if not email or not password:
        return _redirect(error="garmin_credentials_required", section="garmin")
    store_password = save_credentials.strip().lower() in ("on", "true", "1", "yes")
    try:
        await asyncio.to_thread(
            garmin_login,
            email,
            password,
            ctx,
            save_credentials=store_password,
            store_password=store_password,
        )
    except Exception as exc:
        logger.warning("Garmin login from settings failed for %s: %s", ctx.user_id, exc)
        return _redirect(error="garmin_login_failed", section="garmin")
    msg = "garmin_connected"
    if store_password:
        from getsync.credentials.garmin import garmin_auto_login_configured

        if not garmin_auto_login_configured(ctx):
            msg = "garmin_connected_no_vault"
    user = _store().get_user(ctx.user_id)
    audit_log(
        _store(),
        "settings_garmin_connected",
        f"save_credentials={store_password} ip={request_ip(request)}",
        user_id=ctx.user_id,
        subject=user.slug if user else ctx.user_id,
    )
    return _redirect(msg, section="garmin", anchor="garmin-session")


@router.post("/garmin/refresh", include_in_schema=False)
async def garmin_refresh(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    await asyncio.to_thread(refresh_web_session, ctx, force=True, trigger="settings")
    return _redirect("garmin_refreshed", section="garmin", anchor="garmin-session")


@router.post("/garmin/disconnect", include_in_schema=False)
async def garmin_disconnect(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    session_file = ctx.garmin_web_dir / "session.json"
    if session_file.is_file():
        session_file.unlink()
    garth = ctx.garth_dir
    if garth.is_dir():
        shutil.rmtree(garth)
    garth.mkdir(parents=True, exist_ok=True)
    from getsync.credentials.garmin import clear_garmin_credentials

    clear_garmin_credentials(ctx)
    user = _store().get_user(ctx.user_id)
    audit_log(
        _store(),
        "settings_garmin_disconnected",
        f"ip={request_ip(request)}",
        user_id=ctx.user_id,
        subject=user.slug if user else ctx.user_id,
    )
    return _redirect("garmin_disconnected", section="garmin")
