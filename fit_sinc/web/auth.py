"""Session auth for /app (users) and /admin (operator)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from fit_sinc.config import get_settings
from fit_sinc.users.context import UserContext, resolve_user_context

SESSION_USER_KEY = "user_id"
SESSION_ADMIN_KEY = "admin"


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


def is_admin_session(request: Request) -> bool:
    return bool(request.session.get(SESSION_ADMIN_KEY))


def login_user(request: Request, user_id: str) -> None:
    request.session[SESSION_USER_KEY] = user_id


def logout_user(request: Request) -> None:
    request.session.pop(SESSION_USER_KEY, None)


def login_admin(request: Request) -> None:
    request.session[SESSION_ADMIN_KEY] = True


def logout_admin(request: Request) -> None:
    request.session.pop(SESSION_ADMIN_KEY, None)


def verify_admin_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    if not settings.admin_password:
        return False
    return (
        username.strip() == settings.admin_username
        and password == settings.admin_password
    )


def install_auth_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def _auth_guard(request: Request, call_next):
        path = request.url.path
        if path.startswith("/static") or path in ("/favicon.ico", "/health"):
            return await call_next(request)
        if path.startswith("/webhooks"):
            return await call_next(request)
        if path.startswith("/ui-preview"):
            return await call_next(request)

        if path.startswith("/admin"):
            if path in ("/admin/login",) or path.startswith("/admin/login?"):
                return await call_next(request)
            if not is_admin_session(request):
                return RedirectResponse("/admin/login", status_code=303)
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
            target = "/app" + path
            return RedirectResponse(target, status_code=307)

        return await call_next(request)
