"""Self-service registration (Phase 2.1 / 5b.3)."""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from getsync.config import get_settings
from getsync.state.store import Store
from getsync.users.bootstrap import registration_is_open
from getsync.users.slug import allocate_unique_slug, slug_from_email
from getsync.users.locale import DEFAULT_LOCALE, normalize_locale
from getsync.web.app_i18n import register_strings
from getsync.web.site_i18n import LANG_COOKIE, lang_from_request, landing_strings
from getsync.web.auth import login_user, user_context_from_session
from getsync.web.rate_limit import register_attempt_allowed, register_retry_after_sec
from getsync.web.templating import render_template

logger = logging.getLogger("getsync.web.register")

router = APIRouter(tags=["register"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LEN = 8
_LANG_COOKIE_MAX_AGE = 365 * 24 * 3600
_REGISTER_PATH = "/register"


def _store() -> Store:
    return Store(get_settings().db_path)


def _set_lang_cookie(response: HTMLResponse, lang: str) -> None:
    response.set_cookie(
        LANG_COOKIE,
        lang,
        max_age=_LANG_COOKIE_MAX_AGE,
        httponly=False,
        samesite="lax",
    )


def _render_page(
    *,
    closed: bool,
    lang: str,
    error: str = "",
    email: str = "",
    display_name: str = "",
    form: dict[str, str] | None = None,
) -> str:
    form_t = register_strings(lang)
    if form is None and not closed:
        form = {
            "email": email,
            "display_name": display_name,
        }
    return render_template(
        "pages/site/register.html",
        closed=closed,
        registration_open=registration_is_open(),
        form=form,
        error=error,
        lang=lang,
        lang_next_path=_REGISTER_PATH,
        active_nav="signup" if not closed else None,
        t=landing_strings(lang),
        form_t=form_t,
    )


def _render_closed(lang: str) -> str:
    return _render_page(closed=True, lang=lang)


def _render_form(
    lang: str,
    *,
    error: str = "",
    email: str = "",
    display_name: str = "",
) -> str:
    return _render_page(
        closed=False,
        lang=lang,
        error=error,
        email=email,
        display_name=display_name,
    )


def _page_response(
    html: str,
    *,
    lang: str | None = None,
    resolved: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    response = HTMLResponse(html, status_code=status_code)
    if lang is not None and resolved is not None:
        _set_lang_cookie(response, resolved)
    return response


@router.get("/register", response_class=HTMLResponse, response_model=None, include_in_schema=False)
async def register_form(
    request: Request,
    lang: str | None = Query(None),
):
    if user_context_from_session(request):
        return RedirectResponse("/app/", status_code=303)
    resolved = lang_from_request(request, lang)
    if not registration_is_open():
        return _page_response(_render_closed(resolved), status_code=403)
    html = _render_form(resolved)
    return _page_response(html, lang=lang, resolved=resolved)


@router.post("/register", response_model=None, include_in_schema=False)
async def register_submit(
    request: Request,
    email: str = Form(""),
    display_name: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
):
    if user_context_from_session(request):
        return RedirectResponse("/app/", status_code=303)

    lang = lang_from_request(request, None)
    t = register_strings(lang)

    if not registration_is_open():
        return _page_response(_render_closed(lang), status_code=403)

    email_clean = email.strip().lower()
    display = display_name.strip()

    if not register_attempt_allowed(request):
        wait = register_retry_after_sec(request)
        return _page_response(
            _render_form(
                lang,
                error=t["error_rate_limit"].format(wait=wait),
                email=email_clean,
                display_name=display,
            ),
            status_code=429,
        )

    if not _EMAIL_RE.match(email_clean):
        return _page_response(
            _render_form(lang, error=t["error_invalid_email"], email=email_clean),
            status_code=400,
        )
    if len(password) < _MIN_PASSWORD_LEN:
        return _page_response(
            _render_form(
                lang,
                error=t["error_password_short"].format(min_len=_MIN_PASSWORD_LEN),
                email=email_clean,
                display_name=display,
            ),
            status_code=400,
        )
    if password != password_confirm:
        return _page_response(
            _render_form(
                lang,
                error=t["error_password_mismatch"],
                email=email_clean,
                display_name=display,
            ),
            status_code=400,
        )

    reg_locale = normalize_locale(request.cookies.get(LANG_COOKIE, DEFAULT_LOCALE))

    store = _store()
    if store.get_user_by_email(email_clean):
        return _page_response(
            _render_form(
                lang,
                error=t["error_email_taken"],
                email=email_clean,
                display_name=display,
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
            locale=reg_locale,
            is_admin=False,
        )
    except ValueError as exc:
        return _page_response(
            _render_form(
                lang,
                error=str(exc),
                email=email_clean,
                display_name=display,
            ),
            status_code=400,
        )
    except Exception:
        logger.exception("register failed for %s", email_clean)
        return _page_response(
            _render_form(
                lang,
                error=t["error_create_failed"],
                email=email_clean,
                display_name=display,
            ),
            status_code=500,
        )

    login_user(request, user.id)
    logger.info("registered user id=%s slug=%s email=%s", user.id, user.slug, user.email)
    return RedirectResponse("/app/", status_code=303)
