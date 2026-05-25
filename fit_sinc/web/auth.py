"""Session auth: one login for /app; admin via users.is_admin."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from fit_sinc.config import get_settings
from fit_sinc.state.store import Store
from fit_sinc.users.context import UserContext, resolve_user_context
from fit_sinc.users.models import UserRow
from fit_sinc.web.templating import render_template

SESSION_USER_KEY = "user_id"
APP_ADMIN_PREFIX = "/app/admin"


def install_sessions(app: FastAPI) -> None:
    settings = get_settings()
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie="fit_sinc_session",
        max_age=14 * 24 * 3600,
        same_site="lax",
        https_only=False,
    )


def user_context_from_session(request: Request) -> UserContext | None:
    uid = request.session.get(SESSION_USER_KEY)
    if not uid:
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
            if path in ("/app/login",) or path.startswith("/app/login?"):
                return await call_next(request)
            if not user_context_from_session(request):
                return RedirectResponse("/app/login", status_code=303)
            return await call_next(request)

        if path == "/":
            if user_context_from_session(request):
                return RedirectResponse("/app/", status_code=303)
            return RedirectResponse("/app/login", status_code=303)

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
