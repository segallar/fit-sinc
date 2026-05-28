"""Strava OAuth 2.0 (Phase 0 spike + **3.9.3c**)."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
DEAUTHORIZE_URL = "https://www.strava.com/oauth/deauthorize"
API_BASE = "https://www.strava.com/api/v3"

DEFAULT_SCOPE = "read,activity:read,activity:read_all,activity:write"


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str
    expires_at: float
    athlete_id: int
    obtained_at: float

    @classmethod
    def from_response(cls, payload: dict[str, Any]) -> TokenSet:
        athlete = payload.get("athlete") or {}
        athlete_id = athlete.get("id") if isinstance(athlete, dict) else None
        expires_at = payload.get("expires_at")
        if expires_at is None:
            expires_in = int(payload.get("expires_in", 0))
            expires_at = time.time() + expires_in
        return cls(
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]),
            expires_at=float(expires_at),
            athlete_id=int(athlete_id or 0),
            obtained_at=time.time(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "athlete_id": self.athlete_id,
            "obtained_at": self.obtained_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenSet:
        return cls(
            access_token=str(data["access_token"]),
            refresh_token=str(data["refresh_token"]),
            expires_at=float(data["expires_at"]),
            athlete_id=int(data.get("athlete_id") or 0),
            obtained_at=float(data.get("obtained_at", 0)),
        )

    def is_expired(self, skew_seconds: int = 120) -> bool:
        return time.time() >= self.expires_at - skew_seconds


class StravaOAuth:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: str = DEFAULT_SCOPE,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope

    def build_authorize_url(self, state: str | None = None) -> tuple[str, str]:
        state = state or secrets.token_urlsafe(16)
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "approval_prompt": "auto",
            "scope": self.scope,
            "state": state,
        }
        return f"{AUTH_URL}?{urlencode(params)}", state

    async def exchange_code(self, code: str) -> TokenSet:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(TOKEN_URL, data=data)
            response.raise_for_status()
            return TokenSet.from_response(response.json())

    async def refresh(self, refresh_token: str) -> TokenSet:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(TOKEN_URL, data=data)
            response.raise_for_status()
            return TokenSet.from_response(response.json())

    async def deauthorize(self, access_token: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                DEAUTHORIZE_URL,
                params={"access_token": access_token},
            )
            response.raise_for_status()
