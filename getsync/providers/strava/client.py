"""Per-user Strava OAuth tokens + REST client (**3.9.3c**)."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, date, datetime
from typing import Any

import httpx

from getsync.providers.strava.oauth import API_BASE, DEFAULT_SCOPE, StravaOAuth, TokenSet
from getsync.storage import load_json, save_json
from getsync.users.context import UserContext, as_context

UPLOAD_POLL_INTERVAL_SEC = 1.0
UPLOAD_POLL_TIMEOUT_SEC = 90.0


class StravaNotConnectedError(RuntimeError):
    pass


class StravaClient:
    def __init__(self, ctx: UserContext | None = None) -> None:
        self.ctx = as_context(ctx)

    def _oauth(self) -> StravaOAuth:
        settings = self.ctx.settings
        redirect = settings.strava_redirect_uri.strip() or "http://127.0.0.1:8765/callback"
        scope = settings.strava_scope.strip() or DEFAULT_SCOPE
        return StravaOAuth(
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            redirect_uri=redirect,
            scope=scope,
        )

    def load_tokens(self) -> TokenSet | None:
        data = load_json(self.ctx.strava_tokens_path)
        if not data:
            return None
        return TokenSet.from_dict(data)

    def save_tokens(self, tokens: TokenSet) -> None:
        path = self.ctx.strava_tokens_path
        path.parent.mkdir(parents=True, exist_ok=True)
        save_json(path, tokens.to_dict())

    def clear_tokens(self) -> None:
        path = self.ctx.strava_tokens_path
        if path.is_file():
            path.unlink()

    def status(self) -> dict[str, Any]:
        tokens = self.load_tokens()
        if not tokens:
            return {
                "connected": False,
                "expired": False,
                "athlete_id": None,
                "expires_at": None,
                "reason": "no tokens",
            }
        expired = tokens.is_expired()
        return {
            "connected": not expired,
            "expired": expired,
            "athlete_id": tokens.athlete_id or None,
            "expires_at": tokens.expires_at,
            "reason": "token expired" if expired else None,
        }

    async def ensure_tokens(self) -> TokenSet:
        tokens = self.load_tokens()
        if tokens is None:
            raise StravaNotConnectedError(
                f"Strava not connected for user {self.ctx.user_id} — connect in Settings"
            )
        if tokens.is_expired():
            tokens = await self._oauth().refresh(tokens.refresh_token)
            self.save_tokens(tokens)
        return tokens

    async def list_activities(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        tokens = await self.ensure_tokens()
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if date_from is not None:
            params["after"] = _date_to_unix(date_from)
        if date_to is not None:
            params["before"] = _date_to_unix(date_to, end_of_day=True)
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{API_BASE}/athlete/activities",
                params=params,
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)]

    async def upload_fit(
        self,
        fit: bytes,
        filename: str,
        *,
        external_id: str,
        name: str | None = None,
        activity_type: str | None = None,
    ) -> dict[str, Any]:
        tokens = await self.ensure_tokens()
        data: dict[str, str] = {
            "data_type": "fit",
            "external_id": external_id,
        }
        if name:
            data["name"] = name
        if activity_type:
            data["activity_type"] = activity_type
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{API_BASE}/uploads",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
                data=data,
                files={"file": (filename, fit, "application/octet-stream")},
            )
            response.raise_for_status()
            upload = response.json()
        if not isinstance(upload, dict) or upload.get("id") is None:
            return upload if isinstance(upload, dict) else {"raw": upload}
        return await self.poll_upload(int(upload["id"]), access_token=tokens.access_token)

    async def poll_upload(
        self,
        upload_id: int,
        *,
        access_token: str | None = None,
        timeout_sec: float = UPLOAD_POLL_TIMEOUT_SEC,
    ) -> dict[str, Any]:
        token = access_token
        if not token:
            token = (await self.ensure_tokens()).access_token
        deadline = time.time() + timeout_sec
        last: dict[str, Any] = {}
        async with httpx.AsyncClient(timeout=60) as client:
            while time.time() < deadline:
                response = await client.get(
                    f"{API_BASE}/uploads/{upload_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                last = response.json()
                if not isinstance(last, dict):
                    break
                if last.get("activity_id"):
                    return last
                msg = str(last.get("status") or "")
                if last.get("error") or "error" in msg.lower():
                    return last
                await asyncio.sleep(UPLOAD_POLL_INTERVAL_SEC)
        return last


def _date_to_unix(value: date, *, end_of_day: bool = False) -> int:
    if end_of_day:
        dt = datetime(value.year, value.month, value.day, 23, 59, 59, tzinfo=UTC)
    else:
        dt = datetime(value.year, value.month, value.day, 0, 0, 0, tzinfo=UTC)
    return int(dt.timestamp())
