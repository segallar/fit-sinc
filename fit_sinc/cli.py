import asyncio
import json
import logging
import secrets
import webbrowser
from getpass import getpass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

import typer

from fit_sinc.config import get_settings
from fit_sinc.garmin.session import garmin_login, garmin_status
from fit_sinc.garmin.web_session import import_web_cookies, web_login as garmin_web_login
from fit_sinc.garmin.web_refresh import refresh_web_session
from fit_sinc.hammerhead.client import HammerheadClient
from fit_sinc.hammerhead.oauth import HammerheadOAuth
from fit_sinc.state.store import Store
from fit_sinc.sync.service import backfill_since, sync_activity
from fit_sinc.timeutil import format_ts
from fit_sinc.users.bootstrap import apply_bootstrap_admin
from fit_sinc.users.context import UserContext, resolve_user_context
from fit_sinc.users.migrate import infer_hammerhead_user_id, migrate_legacy_files
from fit_sinc.users.models import UserRow

app = typer.Typer(help="fit_sinc — Hammerhead → Garmin Connect")
hammerhead_app = typer.Typer(help="Hammerhead OAuth and API")
garmin_app = typer.Typer(help="Garmin Connect session")
user_app = typer.Typer(help="Tenant users")
app.add_typer(hammerhead_app, name="hammerhead")
app.add_typer(garmin_app, name="garmin")
app.add_typer(user_app, name="user")


def _resolve_user(user: Optional[str]) -> UserContext:
    settings = get_settings()
    uid = user or settings.default_user_id
    if user:
        store = Store(settings.db_path)
        row = store.get_user(user) or store.get_user_by_email(user)
        if row:
            uid = row.id
        else:
            by_slug = next((u for u in store.list_users() if u.slug == user), None)
            if by_slug:
                uid = by_slug.id
    return resolve_user_context(uid)


@app.callback()
def main(
    ctx: typer.Context,
    user: Optional[str] = typer.Option(
        None,
        "--user",
        "-u",
        help="Tenant id, slug, or email (default from DEFAULT_USER_ID)",
    ),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["user_ctx"] = _resolve_user(user)


def _ctx_from_cli(ctx: typer.Context) -> UserContext:
    return ctx.obj["user_ctx"]


def _bootstrap_store() -> Store:
    settings = get_settings()
    store = Store(settings.db_path)
    hh_uid = infer_hammerhead_user_id(settings)
    store.ensure_default_user(hammerhead_user_id=hh_uid)
    migrate_legacy_files(settings, settings.default_user_id)
    apply_bootstrap_admin(store, settings)
    return store


def _find_user(store: Store, identifier: str) -> UserRow | None:
    ident = identifier.strip()
    row = store.get_user(ident) or store.get_user_by_email(ident)
    if row:
        return row
    return next((u for u in store.list_users() if u.slug == ident.lower()), None)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run webhook/UI server."""
    import uvicorn

    _bootstrap_store()
    uvicorn.run("fit_sinc.web.app:app", host=host, port=port)


@user_app.command("list")
def user_list() -> None:
    """List tenant users."""
    store = _bootstrap_store()
    for u in store.list_users():
        hh = u.hammerhead_user_id or "—"
        flags = ""
        if u.is_admin:
            flags += " [admin]"
        if u.disabled:
            flags += " [disabled]"
        typer.echo(f"{u.id}\t{u.slug}\t{u.email}\tHH={hh}{flags}")


@user_app.command("promote-admin")
def user_promote_admin(
    identifier: str = typer.Argument(..., help="User id, slug, or email"),
) -> None:
    """Grant admin role (users.is_admin)."""
    store = _bootstrap_store()
    row = _find_user(store, identifier)
    if not row:
        typer.echo(f"User not found: {identifier}", err=True)
        raise typer.Exit(1)
    store.set_admin(row.id, is_admin=True)
    typer.echo(f"Admin granted: {row.slug} ({row.email})")


@user_app.command("demote-admin")
def user_demote_admin(
    identifier: str = typer.Argument(..., help="User id, slug, or email"),
) -> None:
    """Revoke admin role (cannot demote the last active admin)."""
    store = _bootstrap_store()
    row = _find_user(store, identifier)
    if not row:
        typer.echo(f"User not found: {identifier}", err=True)
        raise typer.Exit(1)
    if row.is_admin and store.count_admins() <= 1:
        typer.echo("Cannot demote the last active admin", err=True)
        raise typer.Exit(1)
    store.set_admin(row.id, is_admin=False)
    typer.echo(f"Admin revoked: {row.slug} ({row.email})")


@user_app.command("create")
def user_create(
    slug: str = typer.Argument(..., help="URL slug (a-z, 0-9, _, -)"),
    email: str = typer.Argument(...),
    display_name: str = typer.Option("", "--name", help="Display name"),
    password: str = typer.Option("", "--password", help="Login password"),
    timezone: str = typer.Option("Europe/Moscow", "--timezone"),
    telegram: str = typer.Option("", "--telegram"),
    hammerhead_user_id: str = typer.Option("", "--hammerhead-user-id"),
) -> None:
    """Create a tenant user."""
    store = _bootstrap_store()
    if not display_name:
        display_name = slug
    if not password:
        password = typer.prompt("Password", hide_input=True)
    row = store.create_user(
        slug=slug,
        display_name=display_name,
        email=email,
        password=password,
        timezone=timezone,
        telegram=telegram or None,
        hammerhead_user_id=hammerhead_user_id or None,
    )
    typer.echo(f"Created user id={row.id} slug={row.slug} email={row.email}")


@hammerhead_app.command("auth-url")
def hammerhead_auth_url(ctx: typer.Context) -> None:
    """Print OAuth authorize URL (manual flow)."""
    settings = get_settings()
    oauth = HammerheadOAuth(
        client_id=settings.hammerhead_client_id,
        client_secret=settings.hammerhead_client_secret,
        redirect_uri=settings.hammerhead_redirect_uri,
        scope=settings.hammerhead_scope,
    )
    url, state = oauth.build_authorize_url()
    user_ctx = _ctx_from_cli(ctx)
    typer.echo(f"user={user_ctx.user_id}")
    typer.echo(f"state={state}")
    typer.echo(url)


@hammerhead_app.command("auth")
def hammerhead_auth(
    ctx: typer.Context,
    port: int = typer.Option(8765, help="Local callback port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open browser"),
) -> None:
    """Run local OAuth flow and save tokens."""
    settings = get_settings()
    user_ctx = _ctx_from_cli(ctx)
    if not settings.hammerhead_client_id or not settings.hammerhead_client_secret:
        typer.echo("Set HAMMERHEAD_CLIENT_ID and HAMMERHEAD_CLIENT_SECRET in .env", err=True)
        raise typer.Exit(1)

    redirect_uri = f"http://127.0.0.1:{port}/callback"
    oauth = HammerheadOAuth(
        client_id=settings.hammerhead_client_id,
        client_secret=settings.hammerhead_client_secret,
        redirect_uri=redirect_uri,
        scope=settings.hammerhead_scope,
    )
    state = secrets.token_urlsafe(16)
    authorize_url, _ = oauth.build_authorize_url(state=state)
    result: dict[str, Any] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != "/callback":
                self.send_error(404)
                return
            params = parse_qs(parsed.query)
            if params.get("state", [""])[0] != state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid state")
                return
            if "error" in params:
                result["error"] = params["error"][0]
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"OAuth error: {result['error']}".encode())
                return
            result["code"] = params.get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>fit_sinc</h1><p>Hammerhead connected. You can close this tab.</p></body></html>"
            )

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    typer.echo(f"User: {user_ctx.user_id}")
    typer.echo(f"Callback: {redirect_uri}")
    typer.echo(f"Open: {authorize_url}")
    if not no_browser:
        webbrowser.open(authorize_url)

    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    while "code" not in result and "error" not in result:
        server.handle_request()

    if result.get("error"):
        typer.echo(f"OAuth denied: {result['error']}", err=True)
        raise typer.Exit(1)

    tokens = asyncio.run(oauth.exchange_code(result["code"]))
    client = HammerheadClient(user_ctx)
    client.save_tokens(tokens)
    store = Store(settings.db_path)
    if tokens.user_id:
        store.update_user(user_ctx.user_id, hammerhead_user_id=str(tokens.user_id))
    typer.echo(f"Saved tokens for hammerhead user_id={tokens.user_id}")
    typer.echo(f"Path: {user_ctx.hammerhead_tokens_path}")


@hammerhead_app.command("status")
def hammerhead_status(ctx: typer.Context) -> None:
    """Show Hammerhead token status."""
    user_ctx = _ctx_from_cli(ctx)
    client = HammerheadClient(user_ctx)
    status = client.status()
    if status.get("expires_at"):
        status["expires_at_msk"] = format_ts(status["expires_at"])
    typer.echo(json.dumps(status, indent=2, default=str))


@garmin_app.command("login")
def garmin_login_cmd(
    ctx: typer.Context,
    email: str = typer.Option("", "--email", envvar="GARMIN_EMAIL"),
    password: str = typer.Option("", "--password", envvar="GARMIN_PASSWORD", hide_input=True),
) -> None:
    """Login to Garmin Connect and save session."""
    user_ctx = _ctx_from_cli(ctx)
    if not email:
        email = typer.prompt("Garmin email")
    if not password:
        password = getpass("Garmin password: ")
    garmin_login(email, password, user_ctx)
    typer.echo(f"OAuth session: {user_ctx.garth_dir}")
    typer.echo(f"Web session: {user_ctx.garmin_web_dir}")


@garmin_app.command("web-login")
def garmin_web_login_cmd(
    ctx: typer.Context,
    email: str = typer.Option("", "--email", envvar="GARMIN_EMAIL"),
    password: str = typer.Option("", "--password", envvar="GARMIN_PASSWORD", hide_input=True),
) -> None:
    """Login web session only (JWT_WEB for FIT upload)."""
    user_ctx = _ctx_from_cli(ctx)
    if not email:
        email = typer.prompt("Garmin email")
    if not password:
        password = getpass("Garmin password: ")
    garmin_web_login(email, password, user_ctx)
    typer.echo(f"Web session saved to {user_ctx.garmin_web_dir}")


@garmin_app.command("import-web-cookie")
def garmin_import_web_cookie(
    ctx: typer.Context,
    jwt_web: str = typer.Argument(..., help="JWT_WEB cookie value from browser DevTools"),
) -> None:
    """Import JWT_WEB cookie (also copy `session` via import-web-cookies for upload)."""
    user_ctx = _ctx_from_cli(ctx)
    try:
        import_web_cookies({"JWT_WEB": jwt_web.strip()}, user_ctx)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    status = garmin_status(user_ctx)
    typer.echo(json.dumps(status, indent=2, default=str))
    if not status.get("upload_ready"):
        typer.echo(
            "Hint: also copy the `session` cookie (Fe26...) and run import-web-cookies",
            err=True,
        )


@garmin_app.command("import-web-cookies")
def garmin_import_web_cookies_cmd(
    ctx: typer.Context,
    cookies_json: str = typer.Argument(
        ...,
        help='JSON object, e.g. \'{"JWT_WEB":"eyJ...","session":"Fe26..."}\'',
    ),
) -> None:
    """Import multiple connect.garmin.com cookies from browser DevTools."""
    user_ctx = _ctx_from_cli(ctx)
    try:
        cookies = json.loads(cookies_json)
    except json.JSONDecodeError:
        typer.echo("Invalid JSON", err=True)
        raise typer.Exit(1)
    if not isinstance(cookies, dict):
        typer.echo("JSON must be an object", err=True)
        raise typer.Exit(1)
    try:
        import_web_cookies({str(k): str(v) for k, v in cookies.items()}, user_ctx)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(garmin_status(user_ctx), indent=2, default=str))


@garmin_app.command("refresh-web")
def garmin_refresh_web_cmd(
    ctx: typer.Context,
    force: bool = typer.Option(False, "--force", help="Refresh even if JWT still valid"),
) -> None:
    """Refresh Garmin JWT_WEB using stored session cookie."""
    user_ctx = _ctx_from_cli(ctx)
    result = refresh_web_session(user_ctx, force=force, trigger="cli")
    if result.get("expires_at"):
        result["expires_at_msk"] = format_ts(result["expires_at"])
    typer.echo(json.dumps(result, indent=2, default=str))
    if not result.get("refreshed") and not garmin_status(user_ctx).get("upload_ready"):
        raise typer.Exit(1)


@garmin_app.command("status")
def garmin_status_cmd(ctx: typer.Context) -> None:
    """Show Garmin session status."""
    status = garmin_status(_ctx_from_cli(ctx))
    for key in ("oauth", "web"):
        block = status.get(key) or {}
        if block.get("token_expires_at"):
            block["token_expires_at_msk"] = format_ts(block["token_expires_at"])
        if block.get("expires_at"):
            block["expires_at_msk"] = format_ts(block["expires_at"])
        if block.get("refreshed_at"):
            block["refreshed_at_msk"] = format_ts(block["refreshed_at"])
    typer.echo(json.dumps(status, indent=2, default=str))


@app.command()
def sync(
    ctx: typer.Context,
    activity_id: str = typer.Option("", "--activity-id", help="Sync single activity"),
    since: str = typer.Option("", "--since", help="Backfill from date YYYY-MM-DD"),
    force: bool = typer.Option(False, "--force", help="Re-sync even if already synced"),
) -> None:
    """Sync activities Hammerhead → Garmin."""
    from datetime import date

    user_ctx = _ctx_from_cli(ctx)
    if activity_id:
        result = asyncio.run(sync_activity(activity_id, force=force, ctx=user_ctx))
        typer.echo(f"{result.activity_id}: {result.status} — {result.message}")
        if result.status == "error":
            raise typer.Exit(1)
        return

    if since:
        try:
            start = date.fromisoformat(since)
        except ValueError:
            typer.echo("Invalid --since, use YYYY-MM-DD", err=True)
            raise typer.Exit(1)
        results = asyncio.run(backfill_since(start, ctx=user_ctx))
        synced = sum(1 for r in results if r.status == "synced")
        skipped = sum(1 for r in results if r.status == "skipped")
        errors = sum(1 for r in results if r.status == "error")
        typer.echo(f"Done: {len(results)} total, synced={synced}, skipped={skipped}, errors={errors}")
        if errors:
            raise typer.Exit(1)
        return

    typer.echo("Specify --activity-id or --since YYYY-MM-DD", err=True)
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
