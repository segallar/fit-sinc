"""Phase 0 spike: verify Strava OAuth + list activities + FIT upload poll.

Usage (after STRAVA_* in .env and app registered at https://www.strava.com/settings/api):

  python scripts/strava_spike.py register-hints
  python scripts/strava_spike.py auth-url
  python scripts/strava_spike.py auth
  python scripts/strava_spike.py list
  python scripts/strava_spike.py upload
  python scripts/strava_spike.py full
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from getsync.config import get_settings  # noqa: E402
from getsync.providers.strava.oauth import (  # noqa: E402
    API_BASE,
    DEFAULT_SCOPE,
    StravaOAuth,
    TokenSet,
)
from getsync.storage import load_json, save_json  # noqa: E402

SPIKE_TOKENS = ROOT / "data" / "spike" / "strava_tokens.json"
SPIKE_FIT = Path(__file__).resolve().parent / "fixtures" / "spike-minimal.fit"


def _oauth(redirect_uri: str) -> StravaOAuth:
    settings = get_settings()
    if not settings.strava_client_id or not settings.strava_client_secret:
        raise SystemExit(
            "Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env "
            "(register at https://www.strava.com/settings/api)"
        )
    return StravaOAuth(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
        redirect_uri=redirect_uri,
        scope=settings.strava_scope or DEFAULT_SCOPE,
    )


def _load_tokens(path: Path) -> TokenSet:
    data = load_json(path)
    if not data:
        raise SystemExit(f"No tokens at {path} — run: python scripts/strava_spike.py auth")
    return TokenSet.from_dict(data)


async def _ensure_token(oauth: StravaOAuth, tokens: TokenSet) -> TokenSet:
    if not tokens.is_expired():
        return tokens
    print("Access token expired — refreshing…")
    return await oauth.refresh(tokens.refresh_token)


def cmd_register_hints() -> None:
    settings = get_settings()
    cli_redirect = settings.strava_redirect_uri or "http://127.0.0.1:8765/callback"
    web_redirect = (
        settings.strava_web_redirect_uri.strip()
        or f"{settings.app_public_url.rstrip('/')}/app/settings/strava/callback"
    )
    print("Strava API app — https://www.strava.com/settings/api")
    print()
    print("Register these Authorization Callback Domain / redirect URIs:")
    print(f"  CLI (spike + getsync strava auth):  {cli_redirect}")
    print(f"  Web (Settings connect, production): {web_redirect}")
    print()
    print(f"Suggested scope: {settings.strava_scope or DEFAULT_SCOPE}")
    print()
    print("Add to .env:")
    print("  STRAVA_CLIENT_ID=<from Strava app>")
    print("  STRAVA_CLIENT_SECRET=<from Strava app>")
    print(f"  STRAVA_REDIRECT_URI={cli_redirect}")
    print(f"  STRAVA_WEB_REDIRECT_URI={web_redirect}")
    print(f"  STRAVA_SCOPE={DEFAULT_SCOPE}")


def cmd_auth_url(port: int) -> None:
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    oauth = _oauth(redirect_uri)
    url, state = oauth.build_authorize_url()
    print(f"redirect_uri={redirect_uri}")
    print(f"state={state}")
    print(url)


def cmd_auth(port: int, no_browser: bool, tokens_path: Path) -> None:
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    oauth = _oauth(redirect_uri)
    state = __import__("secrets").token_urlsafe(16)
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
            result["scope"] = params.get("scope", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>GetSync spike</h1>"
                b"<p>Strava connected. Close this tab.</p></body></html>"
            )

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

    print(f"Callback: {redirect_uri}")
    print(f"Open: {authorize_url}")
    if not no_browser:
        webbrowser.open(authorize_url)

    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    while "code" not in result and "error" not in result:
        server.handle_request()

    if result.get("error"):
        raise SystemExit(f"OAuth denied: {result['error']}")

    tokens = asyncio.run(oauth.exchange_code(result["code"]))
    tokens_path.parent.mkdir(parents=True, exist_ok=True)
    save_json(tokens_path, tokens.to_dict())
    print(f"Granted scope: {result.get('scope') or '—'}")
    print(f"athlete_id={tokens.athlete_id}")
    print(f"expires_at={tokens.expires_at}")
    print(f"Saved: {tokens_path}")


async def _list_activities(tokens: TokenSet, oauth: StravaOAuth) -> None:
    tokens = await _ensure_token(oauth, tokens)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{API_BASE}/athlete/activities",
            params={"page": 1, "per_page": 5},
            headers={"Authorization": f"Bearer {tokens.access_token}"},
        )
        response.raise_for_status()
        items = response.json()
    print(f"GET /athlete/activities → {len(items)} items (page 1, per_page=5)")
    for item in items[:5]:
        print(
            f"  id={item.get('id')} name={item.get('name')!r} "
            f"type={item.get('type')} start={item.get('start_date_local')}"
        )
    if not items:
        print("  (empty — OK for new account; ingest still works)")


async def _upload_fit(tokens: TokenSet, oauth: StravaOAuth, fit_path: Path) -> None:
    tokens = await _ensure_token(oauth, tokens)
    if not fit_path.is_file():
        raise SystemExit(f"FIT fixture missing: {fit_path}")

    fit_bytes = fit_path.read_bytes()
    external_id = f"getsync-spike-{int(time.time())}"
    print(f"POST /uploads external_id={external_id} size={len(fit_bytes)} bytes")

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{API_BASE}/uploads",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
            data={
                "data_type": "fit",
                "external_id": external_id,
                "name": "GetSync spike upload",
                "activity_type": "ride",
            },
            files={"file": (fit_path.name, fit_bytes, "application/octet-stream")},
        )
        response.raise_for_status()
        upload = response.json()

    upload_id = upload.get("id")
    print(f"Upload enqueued id={upload_id} status={upload.get('status')!r}")

    deadline = time.time() + 90
    async with httpx.AsyncClient(timeout=30) as client:
        while time.time() < deadline:
            response = await client.get(
                f"{API_BASE}/uploads/{upload_id}",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            response.raise_for_status()
            status = response.json()
            msg = status.get("status") or status.get("error") or status
            print(f"  poll: {msg}")
            if status.get("activity_id"):
                print(f"  activity_id={status['activity_id']} — upload OK")
                return
            if "error" in status and status.get("error"):
                print(f"  processing error (expected for minimal FIT): {status['error']}")
                return
            if isinstance(msg, str) and "error" in msg.lower():
                print("  processing failed (expected for minimal FIT spike fixture)")
                return
            await asyncio.sleep(1)

    print("  poll timeout — upload accepted but processing still pending")


def cmd_list(tokens_path: Path, port: int) -> None:
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    oauth = _oauth(redirect_uri)
    tokens = _load_tokens(tokens_path)
    asyncio.run(_list_activities(tokens, oauth))


def cmd_upload(tokens_path: Path, port: int, fit_path: Path) -> None:
    redirect_uri = f"http://127.0.0.1:{port}/callback"
    oauth = _oauth(redirect_uri)
    tokens = _load_tokens(tokens_path)
    asyncio.run(_upload_fit(tokens, oauth, fit_path))


def cmd_full(port: int, no_browser: bool, tokens_path: Path, fit_path: Path) -> None:
    cmd_auth(port, no_browser, tokens_path)
    cmd_list(tokens_path, port)
    cmd_upload(tokens_path, port, fit_path)
    print()
    print("Phase 0 spike: full flow completed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Strava API Phase 0 spike")
    parser.add_argument(
        "command",
        choices=("register-hints", "auth-url", "auth", "list", "upload", "full"),
    )
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--tokens", type=Path, default=SPIKE_TOKENS)
    parser.add_argument("--fit", type=Path, default=SPIKE_FIT)
    args = parser.parse_args()

    if args.command == "register-hints":
        cmd_register_hints()
    elif args.command == "auth-url":
        cmd_auth_url(args.port)
    elif args.command == "auth":
        cmd_auth(args.port, args.no_browser, args.tokens)
    elif args.command == "list":
        cmd_list(args.tokens, args.port)
    elif args.command == "upload":
        cmd_upload(args.tokens, args.port, args.fit)
    elif args.command == "full":
        cmd_full(args.port, args.no_browser, args.tokens, args.fit)


if __name__ == "__main__":
    main()
