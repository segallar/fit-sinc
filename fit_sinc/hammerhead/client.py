from typing import Any

import httpx

from fit_sinc.config import Settings, get_settings
from fit_sinc.hammerhead.oauth import HammerheadOAuth, TokenSet
from fit_sinc.storage import load_json, save_json

API_BASE = "https://api.hammerhead.io/v1/api"


class HammerheadClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.oauth = HammerheadOAuth(
            client_id=self.settings.hammerhead_client_id,
            client_secret=self.settings.hammerhead_client_secret,
            redirect_uri=self.settings.hammerhead_redirect_uri,
            scope=self.settings.hammerhead_scope,
        )

    def load_tokens(self) -> TokenSet | None:
        data = load_json(self.settings.hammerhead_tokens_path)
        if not data:
            return None
        return TokenSet.from_dict(data)

    def save_tokens(self, tokens: TokenSet) -> None:
        save_json(self.settings.hammerhead_tokens_path, tokens.to_dict())

    async def ensure_tokens(self) -> TokenSet:
        tokens = self.load_tokens()
        if tokens is None:
            raise RuntimeError("Hammerhead tokens not found — run: fit_sinc hammerhead auth")
        if tokens.is_expired():
            tokens = await self.oauth.refresh(tokens.refresh_token)
            self.save_tokens(tokens)
        return tokens

    async def get_activity(self, activity_id: str) -> dict[str, Any]:
        tokens = await self.ensure_tokens()
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{API_BASE}/activities/{activity_id}",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def download_fit(self, activity_id: str) -> bytes:
        tokens = await self.ensure_tokens()
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(
                f"{API_BASE}/activities/{activity_id}/file",
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            response.raise_for_status()
            return response.content

    async def list_activities(
        self,
        *,
        page: int = 1,
        per_page: int = 50,
        start_date: str | None = None,
    ) -> dict[str, Any]:
        tokens = await self.ensure_tokens()
        params: dict[str, Any] = {"page": page, "perPage": per_page}
        if start_date:
            params["startDate"] = start_date
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.get(
                f"{API_BASE}/activities",
                params=params,
                headers={"Authorization": f"Bearer {tokens.access_token}"},
            )
            response.raise_for_status()
            return response.json()

    def status(self) -> dict[str, Any]:
        tokens = self.load_tokens()
        if tokens is None:
            return {"connected": False, "reason": "no tokens"}
        return {
            "connected": not tokens.is_expired(),
            "user_id": tokens.user_id,
            "expires_at": tokens.expires_at,
            "expired": tokens.is_expired(),
            "client_id_set": bool(self.settings.hammerhead_client_id),
            "webhook_secret_set": bool(self.settings.hammerhead_webhook_secret),
        }
