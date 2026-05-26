"""Public landing at / (getsync.me, app.getsync.me, romansegalla.online)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from getsync.users.bootstrap import registration_is_open
from getsync.web.auth import user_context_from_session
from getsync.web.site_i18n import (
    DEFAULT_LANG,
    LANG_COOKIE,
    landing_strings,
    normalize_lang,
)
from getsync.web.templating import render_template

router = APIRouter(tags=["site"])
APP_PREFIX = "/app"


def _lang_from_request(request: Request, query_lang: str | None) -> str:
    if query_lang:
        return normalize_lang(query_lang)
    cookie = request.cookies.get(LANG_COOKIE)
    if cookie:
        return normalize_lang(cookie)
    accept = request.headers.get("accept-language", "")
    if accept.lower().startswith("ru") or ",ru" in accept.lower():
        return "ru"
    return DEFAULT_LANG


@router.get("/set-lang", include_in_schema=False)
async def set_lang(
    request: Request,
    lang: str = Query("en"),
    next: str = Query("/", alias="next"),
) -> RedirectResponse:
    code = normalize_lang(lang)
    target = next if next.startswith("/") and not next.startswith("//") else "/"
    response = RedirectResponse(target, status_code=303)
    response.set_cookie(
        LANG_COOKIE,
        code,
        max_age=365 * 24 * 3600,
        httponly=False,
        samesite="lax",
    )
    return response


@router.get("/", response_class=HTMLResponse, response_model=None, include_in_schema=False)
async def site_home(
    request: Request,
    lang: str | None = Query(None),
) -> HTMLResponse | RedirectResponse:
    if user_context_from_session(request):
        return RedirectResponse(f"{APP_PREFIX}/", status_code=303)

    resolved = _lang_from_request(request, lang)
    response = HTMLResponse(
        render_template(
            "pages/site/home.html",
            registration_open=registration_is_open(),
            lang=resolved,
            t=landing_strings(resolved),
        )
    )
    if lang is not None:
        response.set_cookie(
            LANG_COOKIE,
            resolved,
            max_age=365 * 24 * 3600,
            httponly=False,
            samesite="lax",
        )
    return response
