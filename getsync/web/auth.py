"""Session auth: one login for /app; admin via users.is_admin."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from getsync.config import get_settings
from getsync.state.store import Store
from getsync.users.context import UserContext, resolve_user_context
from getsync.users.models import UserRow
from getsync.web.legacy_session import legacy_session_payload
from getsync.web.templating import render_template

SESSION_USER_KEY = "user_id"
SESSION_MAX_AGE = 14 * 24 * 3600
APP_ADMIN_PREFIX = "/app/admin"


def install_sessions(app: FastAPI) -> None:
    settings = get_settings()
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="getsync_session",
        max_age=SESSION_MAX_AGE,
        same_site="lax",
        https_only=settings.session_cookie_secure,
    )


def warn_insecure_session_config() -> list[str]:
    """Return human-readable warnings for production session setup."""
    settings = get_settings()
    warnings: list[str] = []
    if settings.session_secret_is_default():
        warnings.append(
            "SESSION_SECRET is default — set a long random value in .env"
        )
    if not settings.session_cookie_secure:
        warnings.append(
            "SESSION_COOKIE_SECURE=false — set SESSION_COOKIE_SECURE=true on HTTPS"
        )
    return warnings


def _session_user_id(request: Request) -> str | None:
    uid = request.session.get(SESSION_USER_KEY)
    if uid:
        return str(uid)
    settings = get_settings()
    legacy = legacy_session_payload(
        request,
        secret_key=settings.session_secret,
        max_age=SESSION_MAX_AGE,
    )
    if legacy:
        legacy_uid = legacy.get(SESSION_USER_KEY)
        if legacy_uid:
            return str(legacy_uid)
    return None


def user_context_from_session(request: Request) -> UserContext | None:
    uid = _session_user_id(request)
    if not uid:
        return None
    user = Store(get_settings().db_path).get_user(str(uid))
    if user is None or user.disabled:
        return None
    return resolve_user_context(str(uid))


def user_row_from_session(request: Request) -> UserRow | None:
    ctx = user_context_from_session(request)
    if not ctx:
        return None
    return Store(ctx.db_path).get_user(ctx.user_id)


def user_is_admin(request: Request) -> bool:
    user = user_row_from_session(request)
    return user is not None and user.is_admin and not user.disabled


def login_user(request: Request, user_id: str) -> None:
    request.session[SESSION_USER_KEY] = user_id


def logout_user(request: Request) -> None:
    request.session.pop(SESSION_USER_KEY, None)


def _admin_forbidden_page() -> HTMLResponse:
    return HTMLResponse(
        render_template("pages/forbidden.html"),
        status_code=403,
    )


def install_auth_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def _auth_guard(request: Request, call_next):
        path = request.url.path
        if path.startswith("/static") or path in ("/favicon.ico", "/health"):
            return await call_next(request)
        if path.startswith("/webhooks"):
            return await call_next(request)
        if path.startswith("/admin"):
            if path.startswith("/admin/login"):
                return RedirectResponse("/app/login", status_code=301)
            suffix = path[len("/admin") :] or "/"
            target = APP_ADMIN_PREFIX + suffix
            if request.url.query:
                target = f"{target}?{request.url.query}"
            return RedirectResponse(target, status_code=301)

        if path.startswith(APP_ADMIN_PREFIX):
            if not user_context_from_session(request):
                return RedirectResponse("/app/login", status_code=303)
            if not user_is_admin(request):
                return _admin_forbidden_page()
            return await call_next(request)

        if path.startswith("/app"):
            if path.startswith("/app/settings/hammerhead/callback"):
                return await call_next(request)
            if path in ("/app/login",) or path.startswith("/app/login?"):
                return await call_next(request)
            if not user_context_from_session(request):
                return RedirectResponse("/app/login", status_code=303)
            return await call_next(request)

        if path == "/":
            return await call_next(request)

        if path == "/register" or path.startswith("/register?"):
            return await call_next(request)

        legacy = (
            "/activities",
            "/log",
            "/session",
        )
        if path == legacy[0] or path.startswith(legacy[0] + "/"):
            return RedirectResponse("/app" + path, status_code=307)
        if path == legacy[1] or path.startswith(legacy[1] + "?"):
            return RedirectResponse("/app" + path, status_code=307)
        if path == legacy[2] or path.startswith(legacy[2]):
            return RedirectResponse("/app" + path, status_code=307)

        return await call_next(request)
