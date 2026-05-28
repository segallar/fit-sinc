"""Strava activity source adapter (planned — OAuth not wired yet)."""

from __future__ import annotations

from datetime import date

from getsync.contracts.activities import ActivityPage
from getsync.contracts.connections import ConnectionStatus
from getsync.providers.strava.client import StravaClient
from getsync.users.context import UserContext


class StravaSource:
    """Activity source — OAuth wired in Settings (**3.9.3c** Phase 1+)."""

    source_id = "strava"

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        from getsync.config import get_settings

        settings = get_settings()
        if not settings.strava_client_id or not settings.strava_client_secret:
            return ConnectionStatus(
                connected=False,
                label="Strava",
                status_text="not configured",
                status_variant="secondary",
            )
        raw = StravaClient(ctx).status()
        connected = bool(raw.get("connected"))
        if connected:
            text, variant = "connected", "success"
        elif raw.get("expired"):
            text, variant = "token expired", "warning"
        elif raw.get("reason") == "no tokens":
            text, variant = "not connected", "secondary"
        else:
            text, variant = "not connected", "secondary"
        details: tuple[tuple[str, str], ...] = ()
        if raw.get("athlete_id"):
            details = (("Athlete id", str(raw["athlete_id"])),)
        return ConnectionStatus(
            connected=connected,
            label="Strava",
            status_text=text,
            status_variant=variant,
            details=details,
        )

    async def fetch_page(
        self,
        ctx: UserContext,
        *,
        page: int = 1,
        per_page: int = 50,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> ActivityPage:
        return ActivityPage(items=(), page=page, total_pages=1)
