"""Per-user Strava token storage (**3.9.3c**)."""

from __future__ import annotations

from typing import Any

from getsync.providers.strava.oauth import TokenSet
from getsync.storage import load_json, save_json
from getsync.users.context import UserContext, as_context


class StravaClient:
    def __init__(self, ctx: UserContext | None = None) -> None:
        self.ctx = as_context(ctx)

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
