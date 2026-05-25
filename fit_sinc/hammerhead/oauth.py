import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

AUTH_URL = "https://api.hammerhead.io/v1/auth/oauth/authorize"
TOKEN_URL = "https://api.hammerhead.io/v1/auth/oauth/token"


@dataclass(frozen=True)
class TokenSet:
    access_token: str
    refresh_token: str
    expires_in: int
    user_id: str
    obtained_at: float

    @classmethod
    def from_response(cls, payload: dict[str, Any]) -> "TokenSet":
        return cls(
            access_token=payload["access_token"],
            refresh_token=payload["refresh_token"],
            expires_in=int(payload["expires_in"]),
            user_id=str(payload.get("user_id", "")),
            obtained_at=time.time(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_in": self.expires_in,
            "user_id": self.user_id,
            "obtained_at": self.obtained_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TokenSet":
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=int(data["expires_in"]),
            user_id=str(data.get("user_id", "")),
            obtained_at=float(data.get("obtained_at", 0)),
        )

    @property
    def expires_at(self) -> float:
        return self.obtained_at + self.expires_in

    def is_expired(self, skew_seconds: int = 120) -> bool:
        return time.time() >= self.expires_at - skew_seconds


class HammerheadOAuth:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: str = "activity:read",
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope

    def build_authorize_url(self, state: str | None = None) -> tuple[str, str]:
        state = state or secrets.token_urlsafe(16)
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
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


def verify_webhook_signature(body: bytes, secret: str, signature: str) -> bool:
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    candidates = {
        digest.hex(),
        digest.hex().upper(),
    }
    import base64

    candidates.add(base64.b64encode(digest).decode("ascii"))
    normalized = signature.removeprefix("sha256=").strip()
    return any(hmac.compare_digest(normalized, candidate) for candidate in candidates)
