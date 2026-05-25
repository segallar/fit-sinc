"""Operator admin UI: user CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from fit_sinc.config import get_settings
from fit_sinc.state.store import Store
from fit_sinc.web import html as H
from fit_sinc.web.auth import login_admin, logout_admin, verify_admin_credentials

router = APIRouter(prefix="/admin", tags=["admin"])


def _store() -> Store:
    return Store(get_settings().db_path)


def _admin_page(title: str, body: str) -> str:
    nav = '<a href="/admin/">Users</a> · <a href="/admin/logout">Logout</a>'
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><title>{H.esc(title)} — fit_sinc admin</title>
<style>{H.BASE_CSS}</style></head><body>
<header class="hero"><h1>fit_sinc admin</h1></header>
<nav>{nav}</nav>
{body}
</body></html>"""


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def admin_login_form(error: str = "") -> str:
    if error:
        err = f'<p class="err">{H.esc(error)}</p>'
    else:
        err = ""
    body = f"""
  <h2>Admin login</h2>
  {err}
  <form method="post" action="/admin/login" class="filters" style="max-width: 360px;">
    <label>Username <input name="username" required autocomplete="username"></label>
    <label>Password <input type="password" name="password" required autocomplete="current-password"></label>
    <button class="btn" type="submit">Sign in</button>
  </form>
"""
    return _admin_page("Login", body)


@router.post("/login", include_in_schema=False)
async def admin_login_submit(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
) -> RedirectResponse:
    if verify_admin_credentials(username, password):
        login_admin(request)
        return RedirectResponse("/admin/", status_code=303)
    return RedirectResponse("/admin/login?error=1", status_code=303)


@router.get("/logout", include_in_schema=False)
async def admin_logout(request: Request) -> RedirectResponse:
    logout_admin(request)
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_users_list() -> str:
    users = _store().list_users()
    rows = []
    for u in users:
        hh = u.hammerhead_user_id or "—"
        tg = u.telegram or "—"
        dis = "yes" if u.disabled else ""
        rows.append(
            f"<tr>"
            f"<td><code>{H.esc(u.id)}</code></td>"
            f"<td>{H.esc(u.slug)}</td>"
            f"<td>{H.esc(u.display_name)}</td>"
            f"<td>{H.esc(u.email)}</td>"
            f"<td>{H.esc(tg)}</td>"
            f"<td>{H.esc(u.timezone)}</td>"
            f"<td class=\"mono\">{H.esc(hh)}</td>"
            f"<td>{dis}</td>"
            f'<td><a class="btn" href="/admin/users/{H.esc(u.id)}/edit">edit</a></td>'
            f"</tr>"
        )
    body = f"""
  <h2>Users</h2>
  <p><a class="btn" href="/admin/users/new">New user</a></p>
  <table>
    <tr><th>id</th><th>slug</th><th>Name</th><th>Email</th><th>Telegram</th><th>TZ</th><th>HH user</th><th>off</th><th></th></tr>
    {"".join(rows) or "<tr><td colspan=9><em>No users</em></td></tr>"}
  </table>
"""
    return _admin_page("Users", body)


@router.get("/users/new", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_new() -> str:
    body = _user_form(action="/admin/users/new", title="New user")
    return _admin_page("New user", body)


@router.post("/users/new", include_in_schema=False)
async def admin_user_create(
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
        body = _user_form(
            action="/admin/users/new",
            title="New user",
            error=str(exc),
            slug=slug,
            display_name=display_name,
            email=email,
            timezone=timezone,
            telegram=telegram,
            hammerhead_user_id=hammerhead_user_id,
        )
        return HTMLResponse(_admin_page("Error", body), status_code=400)
    return RedirectResponse("/admin/", status_code=303)


@router.get("/users/{user_id}/edit", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_edit(user_id: str) -> str:
    user = _store().get_user(user_id)
    if not user:
        return _admin_page("Not found", "<p class=\"err\">User not found</p>")
    body = _user_form(
        action=f"/admin/users/{user_id}/edit",
        title=f"Edit {user.display_name}",
        user_id=user_id,
        slug=user.slug,
        display_name=user.display_name,
        email=user.email,
        timezone=user.timezone,
        telegram=user.telegram or "",
        hammerhead_user_id=user.hammerhead_user_id or "",
        disabled=user.disabled,
        edit=True,
    )
    return _admin_page("Edit user", body)


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
    )
    return RedirectResponse("/admin/", status_code=303)


def _user_form(
    *,
    action: str,
    title: str,
    error: str = "",
    user_id: str = "",
    slug: str = "",
    display_name: str = "",
    email: str = "",
    timezone: str = "Europe/Moscow",
    telegram: str = "",
    hammerhead_user_id: str = "",
    disabled: bool = False,
    edit: bool = False,
) -> str:
    err = f'<p class="err">{H.esc(error)}</p>' if error else ""
    slug_field = (
        f'<label>Slug <input name="slug" value="{H.esc(slug)}" required pattern="[a-z0-9][a-z0-9_-]{{1,62}}"></label>'
        if not edit
        else f"<p>Slug: <code>{H.esc(slug)}</code> (id: <code>{H.esc(user_id)}</code>)</p>"
    )
    pwd_hint = "leave empty to keep" if edit else "required"
    dis = ' checked' if disabled else ""
    return f"""
  <h2>{H.esc(title)}</h2>
  {err}
  <form method="post" action="{H.esc(action)}" class="filters">
    {slug_field}
    <label>Display name <input name="display_name" value="{H.esc(display_name)}" required></label>
    <label>Email <input type="email" name="email" value="{H.esc(email)}" required></label>
    <label>Password <input type="password" name="password" placeholder="{pwd_hint}"></label>
    <label>Timezone <input name="timezone" value="{H.esc(timezone)}"></label>
    <label>Telegram <input name="telegram" value="{H.esc(telegram)}" placeholder="@user"></label>
    <label>Hammerhead user id <input name="hammerhead_user_id" value="{H.esc(hammerhead_user_id)}"></label>
    {"<label><input type=checkbox name=disabled" + dis + "> Disabled</label>" if edit else ""}
    <button class="btn" type="submit">Save</button>
    <a class="btn" href="/admin/">Cancel</a>
  </form>
"""
