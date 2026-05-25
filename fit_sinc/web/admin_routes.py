"""Admin UI under /app/admin (requires users.is_admin)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from fit_sinc.config import get_settings
from fit_sinc.state.store import Store
from fit_sinc.web.auth import APP_ADMIN_PREFIX
from fit_sinc.web.cabinet import render_cabinet

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
    telegram: str = ""
    hammerhead_user_id: str = ""
    disabled: bool = False
    is_admin: bool = False
    edit: bool = False

    @property
    def pwd_hint(self) -> str:
        return "leave empty to keep" if self.edit else "min. 8 characters"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_users_list(request: Request) -> str:
    users = _store().list_users()
    return render_cabinet(
        request,
        "pages/admin/users.html",
        active=f"{A}/",
        users=users,
    )


@router.get("/users/new", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_new(request: Request) -> str:
    form = UserFormData(action=f"{A}/users/new", title="New user")
    return render_cabinet(
        request,
        "pages/admin/user_form.html",
        active=f"{A}/",
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
    telegram: str = Form(""),
    hammerhead_user_id: str = Form(""),
) -> Response:
    store = _store()
    try:
        store.create_user(
            slug=slug,
            display_name=display_name,
            email=email,
            password=password,
            timezone=timezone,
            telegram=telegram or None,
            hammerhead_user_id=hammerhead_user_id or None,
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
            telegram=telegram,
            hammerhead_user_id=hammerhead_user_id,
        )
        return HTMLResponse(
            render_cabinet(request, "pages/admin/user_form.html", active=f"{A}/", form=form),
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
        form=form,
    )


@router.post("/users/{user_id}/edit", include_in_schema=False)
async def admin_user_update(
    user_id: str,
    display_name: str = Form(...),
    email: str = Form(...),
    timezone: str = Form("Europe/Moscow"),
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
        telegram=telegram or None,
        hammerhead_user_id=hammerhead_user_id or None,
        password=password or None,
        disabled=disabled == "on",
        is_admin=is_admin == "on",
    )
    return RedirectResponse(f"{A}/", status_code=303)
