"""Public landing at / (getsync.me, app.getsync.me, romansegalla.online)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from getsync.users.bootstrap import registration_is_open
from getsync.web.auth import user_context_from_session
from getsync.web.templating import render_template

router = APIRouter(tags=["site"])
APP_PREFIX = "/app"


@router.get("/", response_class=HTMLResponse, response_model=None, include_in_schema=False)
async def site_home(request: Request):
    if user_context_from_session(request):
        return RedirectResponse(f"{APP_PREFIX}/", status_code=303)
    return render_template(
        "pages/site/home.html",
        registration_open=registration_is_open(),
    )
