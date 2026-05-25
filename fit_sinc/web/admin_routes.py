"""Admin UI under /app/admin (requires users.is_admin)."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from fit_sinc.config import get_settings
from fit_sinc.state.store import Store
from fit_sinc.web import html as H
from fit_sinc.web.auth import APP_ADMIN_PREFIX, user_row_from_session

router = APIRouter(prefix=APP_ADMIN_PREFIX, tags=["admin"])
A = APP_ADMIN_PREFIX


def _store() -> Store:
    return Store(get_settings().db_path)


def _admin_page(
    request: Request,
    title: str,
    body: str,
    *,
    active: str = "",
) -> str:
    return H.page(
        title,
        body,
        active=active,
        prefix="/app",
        show_admin=True,
        admin_active=active or "/admin",
        current_user=user_row_from_session(request),
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def admin_users_list(request: Request) -> str:
    users = _store().list_users()
    rows = []
    for u in users:
        hh = u.hammerhead_user_id or "—"
        tg = u.telegram or "—"
        dis = "yes" if u.disabled else ""
        adm = "yes" if u.is_admin else ""
        rows.append(
            f"<tr>"
            f"<td><code>{H.esc(u.id)}</code></td>"
            f"<td>{H.esc(u.slug)}</td>"
            f"<td>{H.esc(u.display_name)}</td>"
            f"<td>{H.esc(u.email)}</td>"
            f"<td>{H.esc(tg)}</td>"
            f"<td>{H.esc(u.timezone)}</td>"
            f"<td class=\"mono\">{H.esc(hh)}</td>"
            f"<td>{adm}</td>"
            f"<td>{dis}</td>"
            f'<td><a class="btn" href="{A}/users/{H.esc(u.id)}/edit">edit</a></td>'
            f"</tr>"
        )
    body = f"""
  <h2>Users</h2>
  <p><a class="btn" href="{A}/users/new">New user</a></p>
  <table>
    <tr><th>id</th><th>slug</th><th>Name</th><th>Email</th><th>Telegram</th>
        <th>TZ</th><th>HH user</th><th>admin</th><th>off</th><th></th></tr>
    {"".join(rows) or "<tr><td colspan=10><em>No users</em></td></tr>"}
  </table>
"""
    return _admin_page(request, "Admin — Users", body, active="/admin")


@router.get("/users/new", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_new(request: Request) -> str:
    body = _user_form(action=f"{A}/users/new", title="New user")
    return _admin_page(request, "New user", body, active="/admin")


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
        body = _user_form(
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
            _admin_page(request, "Error", body),
            status_code=400,
        )
    return RedirectResponse(f"{A}/", status_code=303)


@router.get("/users/{user_id}/edit", response_class=HTMLResponse, include_in_schema=False)
async def admin_user_edit(request: Request, user_id: str) -> str:
    user = _store().get_user(user_id)
    if not user:
        return _admin_page(request, "Not found", '<p class="err">User not found</p>')
    body = _user_form(
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
    return _admin_page(request, "Edit user", body, active="/admin")


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
    is_admin: bool = False,
    edit: bool = False,
) -> str:
    err = f'<p class="err">{H.esc(error)}</p>' if error else ""
    pwd_required = "" if edit else " required"
    pwd_hint = "leave empty to keep" if edit else "min. 8 characters"
    dis = " checked" if disabled else ""
    adm = " checked" if is_admin else ""

    if edit:
        slug_block = f"""
      <p class="form-hint">Slug: <code>{H.esc(slug)}</code> · id: <code>{H.esc(user_id)}</code></p>"""
        account_fields = f"""
        <label>Display name
          <input name="display_name" value="{H.esc(display_name)}" required autocomplete="name">
        </label>
        <label>Email
          <input type="email" name="email" value="{H.esc(email)}" required autocomplete="email">
        </label>
        <label class="span-2">Password
          <input type="password" name="password" placeholder="{H.esc(pwd_hint)}" autocomplete="new-password">
          <p class="form-hint">{H.esc(pwd_hint)}</p>
        </label>
        {H.timezone_field("timezone", timezone)}"""
        flags_section = f"""
    <fieldset class="form-section">
      <legend>Access</legend>
      <div class="form-grid">
        <label><input type="checkbox" name="disabled"{dis}> Disabled</label>
        <label><input type="checkbox" name="is_admin"{adm}> Administrator</label>
      </div>
    </fieldset>"""
    else:
        slug_block = ""
        account_fields = f"""
        <label>Slug
          <input name="slug" value="{H.esc(slug)}" required pattern="[a-z0-9][a-z0-9_-]{{1,62}}" autocomplete="off">
          <p class="form-hint">Lowercase letters, digits, <code>_</code> and <code>-</code>; used in paths.</p>
        </label>
        <label>Display name
          <input name="display_name" value="{H.esc(display_name)}" required autocomplete="name">
        </label>
        <label>Email
          <input type="email" name="email" value="{H.esc(email)}" required autocomplete="email">
        </label>
        <label>Password
          <input type="password" name="password"{pwd_required} autocomplete="new-password">
          <p class="form-hint">{H.esc(pwd_hint)}</p>
        </label>
        {H.timezone_field("timezone", timezone)}"""
        flags_section = ""

    return f"""
  <h2>{H.esc(title)}</h2>
  {err}
  <div class="form-card">
  <form method="post" action="{H.esc(action)}" class="user-form">
    <fieldset class="form-section">
      <legend>Account</legend>
      <div class="form-grid">
        {slug_block}
        {account_fields}
      </div>
    </fieldset>
    <fieldset class="form-section">
      <legend>Contacts</legend>
      <div class="form-grid">
        <label class="span-2">Telegram
          <input name="telegram" value="{H.esc(telegram)}" placeholder="@username" autocomplete="off">
        </label>
      </div>
    </fieldset>
    <fieldset class="form-section">
      <legend>Hammerhead</legend>
      <div class="form-grid">
        <label class="span-2">Hammerhead user id
          <input name="hammerhead_user_id" value="{H.esc(hammerhead_user_id)}" placeholder="from webhook payload userId">
          <p class="form-hint">Optional. Links webhook events to this account.</p>
        </label>
      </div>
    </fieldset>
    {flags_section}
    <div class="form-actions">
      <button class="btn" type="submit">Save</button>
      <a class="btn" href="{A}/">Cancel</a>
    </div>
  </form>
  </div>
"""
