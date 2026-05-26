"""Self-service registration (Phase 2.1 / 5b.3)."""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from getsync.config import get_settings
from getsync.state.store import Store
from getsync.users.bootstrap import registration_is_open
from getsync.users.slug import allocate_unique_slug, slug_from_email
from getsync.users.timezones import DEFAULT_TIMEZONE, normalize_timezone
from getsync.web.auth import login_user, user_context_from_session
from getsync.web.rate_limit import register_attempt_allowed, register_retry_after_sec
from getsync.web.templating import render_template

logger = logging.getLogger("getsync.web.register")

router = APIRouter(tags=["register"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 8


def _store() -> Store:
    return Store(get_settings().db_path)


def _render_closed() -> str:
    return render_template(
        "pages/site/register.html",
        closed=True,
        registration_open=False,
        form=None,
        error="",
    )


def _render_form(
    *,
    error: str = "",
    email: str = "",
    display_name: str = "",
    timezone: str = DEFAULT_TIMEZONE,
) -> str:
    return render_template(
        "pages/site/register.html",
        closed=False,
        registration_open=True,
        form={
            "email": email,
            "display_name": display_name,
            "timezone": timezone,
        },
        error=error,
    )


@router.get("/register", response_class=HTMLResponse, response_model=None, include_in_schema=False)
async def register_form(request: Request):
    if user_context_from_session(request):
        return RedirectResponse("/app/", status_code=303)
    if not registration_is_open():
        return HTMLResponse(_render_closed(), status_code=403)
    return HTMLResponse(_render_form())


@router.post("/register", response_model=None, include_in_schema=False)
async def register_submit(
    request: Request,
    email: str = Form(""),
    display_name: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
    timezone: str = Form(DEFAULT_TIMEZONE),
):
    if user_context_from_session(request):
        return RedirectResponse("/app/", status_code=303)

    if not registration_is_open():
        return HTMLResponse(_render_closed(), status_code=403)

    email_clean = email.strip().lower()
    display = display_name.strip()
    tz = normalize_timezone(timezone or DEFAULT_TIMEZONE)

    if not register_attempt_allowed(request):
        wait = register_retry_after_sec(request)
        return HTMLResponse(
            _render_form(
                error=f"Слишком много попыток. Подождите {wait} с.",
                email=email_clean,
                display_name=display,
                timezone=tz,
            ),
            status_code=429,
        )

    if not _EMAIL_RE.match(email_clean):
        return HTMLResponse(
            _render_form(error="Укажите корректный email.", email=email_clean, timezone=tz),
            status_code=400,
        )
    if len(password) < _MIN_PASSWORD_LEN:
        return HTMLResponse(
            _render_form(
                error=f"Пароль не короче {_MIN_PASSWORD_LEN} символов.",
                email=email_clean,
                display_name=display,
                timezone=tz,
            ),
            status_code=400,
        )
    if password != password_confirm:
        return HTMLResponse(
            _render_form(
                error="Пароли не совпадают.",
                email=email_clean,
                display_name=display,
                timezone=tz,
            ),
            status_code=400,
        )

    store = _store()
    if store.get_user_by_email(email_clean):
        return HTMLResponse(
            _render_form(
                error="Аккаунт с таким email уже есть. Войдите или восстановите доступ.",
                email=email_clean,
                display_name=display,
                timezone=tz,
            ),
            status_code=400,
        )

    slug = allocate_unique_slug(store, slug_from_email(email_clean))
    name = display or email_clean.split("@", 1)[0].replace(".", " ").replace("_", " ").title()

    try:
        user = store.create_user(
            slug=slug,
            display_name=name,
            email=email_clean,
            password=password,
            timezone=tz,
            is_admin=False,
        )
    except ValueError as exc:
        return HTMLResponse(
            _render_form(
                error=str(exc),
                email=email_clean,
                display_name=display,
                timezone=tz,
            ),
            status_code=400,
        )
    except Exception as exc:
        logger.exception("register failed for %s", email_clean)
        return HTMLResponse(
            _render_form(
                error="Не удалось создать аккаунт. Попробуйте позже.",
                email=email_clean,
                display_name=display,
                timezone=tz,
            ),
            status_code=500,
        )

    login_user(request, user.id)
    logger.info("registered user id=%s slug=%s email=%s", user.id, user.slug, user.email)
    return RedirectResponse("/app/", status_code=303)
