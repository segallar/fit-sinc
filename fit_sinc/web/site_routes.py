"""Public landing at / (romansegalla.online, fit.romansegalla.online)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from fit_sinc.web.auth import user_context_from_session
from fit_sinc.web.templating import render_template

router = APIRouter(tags=["site"])
APP_PREFIX = "/app"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def site_home(request: Request, error: str = "") -> str | RedirectResponse:
    if user_context_from_session(request):
        return RedirectResponse(f"{APP_PREFIX}/", status_code=303)
    return render_template(
        "pages/site/home.html",
        prefix=APP_PREFIX,
        error=bool(error),
    )
