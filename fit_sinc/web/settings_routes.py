"""User settings: profile, password, Hammerhead/Garmin connections."""

from __future__ import annotations

import asyncio
import shutil

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from fit_sinc.config import get_settings
from fit_sinc.garmin.web_refresh import refresh_web_session
from fit_sinc.hammerhead.client import HammerheadClient
from fit_sinc.hammerhead.oauth import HammerheadOAuth
from fit_sinc.state.store import Store
from fit_sinc.storage import save_json
from fit_sinc.users.context import UserContext
from fit_sinc.web.auth import user_context_from_session
from fit_sinc.web.connections import connection_settings_view
from fit_sinc.web.cabinet import render_cabinet
from fit_sinc.web.oauth_state import sign_hammerhead_oauth_state, verify_hammerhead_oauth_state

router = APIRouter(prefix="/app/settings", tags=["settings"])
P = "/app/settings"


def _store() -> Store:
    return Store(get_settings().db_path)


def _ctx(request: Request) -> UserContext:
    ctx = user_context_from_session(request)
    if not ctx:
        raise HTTPException(status_code=401)
    return ctx


def _redirect(msg: str = "", *, error: str = "") -> RedirectResponse:
    params: dict[str, str] = {}
    if msg:
        params["msg"] = msg
    if error:
        params["error"] = error
    q = H.query_string(params)
    url = f"{P}?{q}" if q else P
    return RedirectResponse(url, status_code=303)


def _flash_from_query(request: Request) -> dict[str, str]:
    flash: dict[str, str] = {}
    msg = request.query_params.get("msg", "").strip()
    err = request.query_params.get("error", "").strip()
    if msg == "profile_saved":
        flash["ok"] = "Profile saved."
    elif msg == "password_changed":
        flash["ok"] = "Password updated."
    elif msg == "hh_connected":
        flash["ok"] = "Hammerhead connected."
    elif msg == "hh_disconnected":
        flash["ok"] = "Hammerhead disconnected."
    elif msg == "garmin_refreshed":
        flash["ok"] = "Garmin session refresh requested."
    elif msg == "garmin_disconnected":
        flash["ok"] = "Garmin sessions removed for this account."
    if err == "hh_not_configured":
        flash["error"] = "Hammerhead OAuth is not configured on the server."
    elif err == "hh_state":
        flash["error"] = "Hammerhead OAuth state invalid or expired."
    elif err == "hh_user_mismatch":
        flash["error"] = "Hammerhead OAuth user mismatch."
    elif err.startswith("hh_"):
        flash["error"] = f"Hammerhead OAuth error: {err[3:]}"
    elif err == "password_too_short":
        flash["error"] = "New password must be at least 8 characters."
    elif err == "password_mismatch":
        flash["error"] = "New passwords do not match."
    elif err == "wrong_current_password":
        flash["error"] = "Current password is incorrect."
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
    return render_cabinet(
        request,
        "pages/app/settings.html",
        active=f"{P}/",
        user=user,
        flash=_flash_from_query(request),
        conn=connection_settings_view(ctx, user),
    )


@router.post("/profile", include_in_schema=False)
async def settings_profile(
    request: Request,
    display_name: str = Form(...),
    email: str = Form(...),
    telegram: str = Form(""),
    timezone: str = Form("Europe/Moscow"),
) -> RedirectResponse:
    ctx = _ctx(request)
    store = _store()
    try:
        store.update_user(
            ctx.user_id,
            display_name=display_name.strip(),
            email=email.strip(),
            telegram=telegram.strip() or None,
            timezone=timezone,
        )
    except Exception as exc:
        return _redirect(error=str(exc))
    return _redirect("profile_saved")


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
        return _redirect(error="password_too_short")
    if new_password != new_password_confirm:
        return _redirect(error="password_mismatch")
    if not _store().verify_user_password(user.email, current_password):
        return _redirect(error="wrong_current_password")
    _store().update_user(ctx.user_id, password=new_password)
    return _redirect("password_changed")


@router.get("/hammerhead/connect", include_in_schema=False)
async def hammerhead_connect(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    settings = get_settings()
    if not settings.hammerhead_client_id or not settings.hammerhead_client_secret:
        return _redirect(error="hh_not_configured")
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
        return _redirect(error=f"hh_{error}")
    uid = verify_hammerhead_oauth_state(state, get_settings().session_secret)
    if not uid:
        return _redirect(error="hh_state")
    session_ctx = user_context_from_session(request)
    if session_ctx and session_ctx.user_id != uid:
        return _redirect(error="hh_user_mismatch")
    if not session_ctx:
        from fit_sinc.web.auth import login_user

        login_user(request, uid)
    if not code:
        return _redirect(error="hh_missing_code")
    oauth = _hammerhead_oauth(request)
    try:
        tokens = await oauth.exchange_code(code)
    except Exception as exc:
        return _redirect(error=str(exc))
    ctx = UserContext(uid, get_settings())
    save_json(ctx.hammerhead_tokens_path, tokens.to_dict())
    hh_uid = tokens.user_id or None
    if hh_uid:
        _store().update_user(uid, hammerhead_user_id=str(hh_uid))
    return _redirect("hh_connected")


@router.post("/hammerhead/disconnect", include_in_schema=False)
async def hammerhead_disconnect(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    path = ctx.hammerhead_tokens_path
    if path.is_file():
        path.unlink()
    return _redirect("hh_disconnected")


@router.post("/garmin/refresh", include_in_schema=False)
async def garmin_refresh(request: Request) -> RedirectResponse:
    ctx = _ctx(request)
    await asyncio.to_thread(refresh_web_session, ctx, force=True, trigger="settings")
    return _redirect("garmin_refreshed")


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
    return _redirect("garmin_disconnected")
