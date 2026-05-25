import asyncio
import json
import logging
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

import typer
from getpass import getpass

from fit_sinc.config import get_settings
from fit_sinc.garmin.session import garmin_login, garmin_status
from fit_sinc.garmin.web_session import import_web_cookies, web_login as garmin_web_login
from fit_sinc.garmin.web_refresh import refresh_web_session
from fit_sinc.hammerhead.client import HammerheadClient
from fit_sinc.hammerhead.oauth import HammerheadOAuth
from fit_sinc.sync.service import backfill_since, sync_activity
from fit_sinc.timeutil import format_ts

app = typer.Typer(help="fit_sinc — Hammerhead → Garmin Connect")
hammerhead_app = typer.Typer(help="Hammerhead OAuth and API")
garmin_app = typer.Typer(help="Garmin Connect session")
app.add_typer(hammerhead_app, name="hammerhead")
app.add_typer(garmin_app, name="garmin")


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Run webhook/UI server."""
    import uvicorn

    uvicorn.run("fit_sinc.web.app:app", host=host, port=port)


@hammerhead_app.command("auth-url")
def hammerhead_auth_url() -> None:
    """Print OAuth authorize URL (manual flow)."""
    settings = get_settings()
    oauth = HammerheadOAuth(
        client_id=settings.hammerhead_client_id,
        client_secret=settings.hammerhead_client_secret,
        redirect_uri=settings.hammerhead_redirect_uri,
        scope=settings.hammerhead_scope,
    )
    url, state = oauth.build_authorize_url()
    typer.echo(f"state={state}")
    typer.echo(url)


@hammerhead_app.command("auth")
def hammerhead_auth(
    port: int = typer.Option(8765, help="Local callback port"),
    no_browser: bool = typer.Option(False, "--no-browser", help="Do not open browser"),
) -> None:
    """Run local OAuth flow and save tokens."""
    settings = get_settings()
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
    client = HammerheadClient(settings)
    client.save_tokens(tokens)
    typer.echo(f"Saved tokens for user_id={tokens.user_id}")
    typer.echo(f"Path: {settings.hammerhead_tokens_path}")


@hammerhead_app.command("status")
def hammerhead_status() -> None:
    """Show Hammerhead token status."""
    client = HammerheadClient()
    status = client.status()
    if status.get("expires_at"):
        status["expires_at_msk"] = format_ts(status["expires_at"])
    typer.echo(json.dumps(status, indent=2, default=str))


@garmin_app.command("login")
def garmin_login_cmd(
    email: str = typer.Option("", "--email", envvar="GARMIN_EMAIL"),
    password: str = typer.Option("", "--password", envvar="GARMIN_PASSWORD", hide_input=True),
) -> None:
    """Login to Garmin Connect and save session."""
    settings = get_settings()
    if not email:
        email = typer.prompt("Garmin email")
    if not password:
        password = getpass("Garmin password: ")
    garmin_login(email, password, settings)
    typer.echo(f"OAuth session: {settings.garth_dir}")
    typer.echo(f"Web session: {settings.data_dir / 'garmin_web'}")


@garmin_app.command("web-login")
def garmin_web_login_cmd(
    email: str = typer.Option("", "--email", envvar="GARMIN_EMAIL"),
    password: str = typer.Option("", "--password", envvar="GARMIN_PASSWORD", hide_input=True),
) -> None:
    """Login web session only (JWT_WEB for FIT upload)."""
    settings = get_settings()
    if not email:
        email = typer.prompt("Garmin email")
    if not password:
        password = getpass("Garmin password: ")
    garmin_web_login(email, password, settings)
    typer.echo(f"Web session saved to {settings.data_dir / 'garmin_web'}")


@garmin_app.command("import-web-cookie")
def garmin_import_web_cookie(
    jwt_web: str = typer.Argument(..., help="JWT_WEB cookie value from browser DevTools"),
) -> None:
    """Import JWT_WEB cookie (also copy `session` via import-web-cookies for upload)."""
    settings = get_settings()
    try:
        import_web_cookies({"JWT_WEB": jwt_web.strip()}, settings)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    status = garmin_status()
    typer.echo(json.dumps(status, indent=2, default=str))
    if not status.get("upload_ready"):
        typer.echo(
            "Hint: also copy the `session` cookie (Fe26...) and run import-web-cookies",
            err=True,
        )


@garmin_app.command("import-web-cookies")
def garmin_import_web_cookies_cmd(
    cookies_json: str = typer.Argument(
        ...,
        help='JSON object, e.g. \'{"JWT_WEB":"eyJ...","session":"Fe26..."}\'',
    ),
) -> None:
    """Import multiple connect.garmin.com cookies from browser DevTools."""
    settings = get_settings()
    try:
        cookies = json.loads(cookies_json)
    except json.JSONDecodeError:
        typer.echo("Invalid JSON", err=True)
        raise typer.Exit(1)
    if not isinstance(cookies, dict):
        typer.echo("JSON must be an object", err=True)
        raise typer.Exit(1)
    try:
        import_web_cookies({str(k): str(v) for k, v in cookies.items()}, settings)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(garmin_status(), indent=2, default=str))


@garmin_app.command("refresh-web")
def garmin_refresh_web_cmd(
    force: bool = typer.Option(False, "--force", help="Refresh even if JWT still valid"),
) -> None:
    """Refresh Garmin JWT_WEB using stored session cookie."""
    settings = get_settings()
    result = refresh_web_session(settings, force=force, trigger="cli")
    if result.get("expires_at"):
        result["expires_at_msk"] = format_ts(result["expires_at"])
    typer.echo(json.dumps(result, indent=2, default=str))
    if not result.get("refreshed") and not garmin_status().get("upload_ready"):
        raise typer.Exit(1)


@garmin_app.command("status")
def garmin_status_cmd() -> None:
    """Show Garmin session status."""
    status = garmin_status()
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
    activity_id: str = typer.Option("", "--activity-id", help="Sync single activity"),
    since: str = typer.Option("", "--since", help="Backfill from date YYYY-MM-DD"),
    force: bool = typer.Option(False, "--force", help="Re-sync even if already synced"),
) -> None:
    """Sync activities Hammerhead → Garmin."""
    from datetime import date

    if activity_id:
        result = asyncio.run(sync_activity(activity_id, force=force))
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
        results = asyncio.run(backfill_since(start))
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
