"""Admin UI under /app/admin (requires users.is_admin)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from getsync.audit import log as audit_log
from getsync.config import get_settings
from getsync.state.store import Store
from getsync.web.auth import APP_ADMIN_PREFIX, user_row_from_session
from getsync.web.cabinet import render_cabinet
from getsync.web.admin_health import admin_health_context, render_admin_health_panel
from getsync.web.admin_log import admin_log_context, render_admin_log_table

router = APIRouter(prefix=APP_ADMIN_PREFIX, tags=["admin"])
A = APP_ADMIN_PREFIX


def _store() -> Store:
    return Store(get_settings().db_path)


@dataclass
class UserFormData:
    action: str
    title: str
    error: str = ""
    user_id: str = ""
    slug: str = ""
    display_name: str = ""
    email: str = ""
    timezone: str = "Europe/Moscow"
    locale: str = "en"
    telegram: str = ""
    hammerhead_user_id: str = ""
    disabled: bool = False
    is_admin: bool = False
    edit: bool = False

    @property
    def pwd_hint(self) -> str:
        return "leave empty to keep" if self.edit else "min. 8 characters"


@router.get("/health", response_class=HTMLResponse, include_in_schema=False)
async def admin_app_health(request: Request) -> str:
    settings = get_settings()
    store = _store()
    return render_cabinet(
        request,
        "pages/admin/health.html",
        active=f"{A}/health",
        admin_section="health",
        **admin_health_context(settings, store),
    )


@router.get("/log", response_class=HTMLResponse, include_in_schema=False)
async def admin_log(
    request: Request,
    log_page: int = Query(1, ge=1),
) -> str:
    store = _store()
    return render_cabinet(
        request,
        "pages/admin/log.html",
        active=f"{A}/log",
        admin_section="log",
        **admin_log_context(
            store,
            user_id=None,
            log_page=log_page,
            pager_path=f"{A}/log",
        ),
    )


@router.get("/log/fragment", response_class=HTMLResponse, include_in_schema=False)
async def admin_log_fragment(
    log_page: int = Query(1, ge=1),
) -> str:
    """HTML fragment for WebSocket-driven log refresh."""
    return render_admin_log_table(_store(), log_page=log_page)


@router.get("/health/fragment", response_class=HTMLResponse, include_in_schema=False)
async def admin_health_fragment() -> str:
    """HTML fragment for WebSocket-driven health refresh."""
    return render_admin_health_panel(get_settings(), _store())


@router.get("/sync-log", include_in_schema=False)
async def admin_sync_log_redirect(log_page: int = Query(1, ge=1)) -> RedirectResponse:
    return RedirectResponse(f"{A}/log?log_page={log_page}#admin-log", status_code=303)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_users_list(request: Request) -> str:
    users = _store().list_users()
    return render_cabinet(
        request,
        "pages/admin/users.html",
        active=f"{A}/",
        admin_section="users",
        users=users,
    )


@router.get("/users/new", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_new(request: Request) -> str:
    form = UserFormData(action=f"{A}/users/new", title="New user")
    return render_cabinet(
        request,
        "pages/admin/user_form.html",
        active=f"{A}/",
        admin_section="users",
        form=form,
    )


@router.post("/users/new", include_in_schema=False)
async def admin_user_create(
    request: Request,
    slug: str = Form(...),
    display_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    timezone: str = Form("Europe/Moscow"),
    locale: str = Form("en"),
    telegram: str = Form(""),
    hammerhead_user_id: str = Form(""),
) -> Response:
    store = _store()
    try:
        user = store.create_user(
            slug=slug,
            display_name=display_name,
            email=email,
            password=password,
            timezone=timezone,
            locale=locale,
            telegram=telegram or None,
            hammerhead_user_id=hammerhead_user_id or None,
        )
        actor = user_row_from_session(request)
        audit_log(
            store,
            "user_created",
            f"email={user.email}",
            user_id=user.id,
            subject=user.slug,
            actor_user_id=actor.id if actor else None,
        )
    except Exception as exc:
        form = UserFormData(
            action=f"{A}/users/new",
            title="New user",
            error=str(exc),
            slug=slug,
            display_name=display_name,
            email=email,
            timezone=timezone,
            locale=locale,
            telegram=telegram,
            hammerhead_user_id=hammerhead_user_id,
        )
        return HTMLResponse(
            render_cabinet(
                request,
                "pages/admin/user_form.html",
                active=f"{A}/",
                admin_section="users",
                form=form,
            ),
            status_code=400,
        )
    return RedirectResponse(f"{A}/", status_code=303)


@router.get("/users/{user_id}/edit", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_edit(request: Request, user_id: str) -> str:
    user = _store().get_user(user_id)
    if not user:
        return render_cabinet(
            request,
            "pages/admin/user_form.html",
            active=f"{A}/",
            admin_section="users",
            form=UserFormData(
                action=f"{A}/users/{user_id}/edit",
                title="Not found",
                error="User not found",
                edit=True,
            ),
        )
    form = UserFormData(
        action=f"{A}/users/{user_id}/edit",
        title=f"Edit {user.display_name}",
        user_id=user_id,
        slug=user.slug,
        display_name=user.display_name,
        email=user.email,
        timezone=user.timezone,
        locale=user.locale,
        telegram=user.telegram or "",
        hammerhead_user_id=user.hammerhead_user_id or "",
        disabled=user.disabled,
        is_admin=user.is_admin,
        edit=True,
    )
    return render_cabinet(
        request,
        "pages/admin/user_form.html",
        active=f"{A}/",
        admin_section="users",
        form=form,
    )


@router.post("/users/{user_id}/edit", include_in_schema=False)
async def admin_user_update(
    request: Request,
    user_id: str,
    display_name: str = Form(...),
    email: str = Form(...),
    timezone: str = Form("Europe/Moscow"),
    locale: str = Form("en"),
    telegram: str = Form(""),
    hammerhead_user_id: str = Form(""),
    password: str = Form(""),
    disabled: str = Form(""),
    is_admin: str = Form(""),
) -> RedirectResponse:
    store = _store()
    store.update_user(
        user_id,
        display_name=display_name,
        email=email,
        timezone=timezone,
        locale=locale,
        telegram=telegram or None,
        hammerhead_user_id=hammerhead_user_id or None,
        password=password or None,
        disabled=disabled == "on",
        is_admin=is_admin == "on",
    )
    target = store.get_user(user_id)
    actor = user_row_from_session(request)
    audit_log(
        store,
        "user_updated",
        f"email={email.strip().lower()}",
        user_id=user_id,
        subject=target.slug if target else user_id,
        actor_user_id=actor.id if actor else None,
    )
    return RedirectResponse(f"{A}/", status_code=303)
