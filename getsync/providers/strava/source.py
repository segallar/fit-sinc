"""Strava activity source adapter."""

from __future__ import annotations

from datetime import date

from getsync.contracts.activities import ActivityPage
from getsync.contracts.connections import ConnectionStatus
from getsync.providers.strava.client import StravaClient
from getsync.providers.strava.normalize import item_to_normalized
from getsync.users.context import UserContext


class StravaSource:
    """Activity source — OAuth + list activities (**3.9.3c**)."""

    source_id = "strava"

    def _client(self, ctx: UserContext) -> StravaClient:
        return StravaClient(ctx)

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
        raw = self._client(ctx).status()
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
        client = self._client(ctx)
        if client.load_tokens() is None:
            return ActivityPage(items=(), page=page, total_pages=1)
        try:
            raw_items = await client.list_activities(
                page=page,
                per_page=per_page,
                date_from=date_from,
                date_to=date_to,
            )
        except Exception as exc:
            return ActivityPage(
                items=(),
                page=page,
                total_pages=1,
                errors=(str(exc),),
            )
        items = tuple(
            row
            for item in raw_items
            if (row := item_to_normalized(item, ctx.user_id)) is not None
        )
        total_pages = page + 1 if len(raw_items) >= per_page else page
        return ActivityPage(
            items=items,
            page=page,
            total_pages=max(1, total_pages),
            total_items=None,
        )
