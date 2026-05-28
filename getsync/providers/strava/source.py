"""Strava activity source adapter (planned — OAuth not wired yet)."""

from __future__ import annotations

from datetime import date

from getsync.contracts.activities import ActivityPage
from getsync.contracts.connections import ConnectionStatus
from getsync.users.context import UserContext


class StravaSource:
    """ActivitySource placeholder until Strava OAuth + API (**3.9.3b** follow-up)."""

    source_id = "strava"

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        return ConnectionStatus(
            connected=False,
            label="Strava",
            status_text="planned",
            status_variant="secondary",
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
