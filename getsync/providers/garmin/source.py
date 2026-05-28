"""Garmin Connect activity source adapter (OAuth list)."""

from __future__ import annotations

import asyncio
from datetime import date

from getsync.contracts.activities import ActivityPage, NormalizedActivity
from getsync.contracts.connections import ConnectionStatus
from getsync.garmin.activities import GarminActivityItem, list_garmin_activities
from getsync.garmin.session import garmin_resume, garmin_status
from getsync.users.context import UserContext


def _item_to_normalized(item: GarminActivityItem, user_id: str) -> NormalizedActivity:
    return NormalizedActivity(
        user_id=user_id,
        source="garmin",
        activity_id=str(item.activity_id),
        name=item.name,
        activity_date=item.activity_date,
        distance=item.distance,
        duration=item.duration,
        activity_type=item.activity_type,
        sync_status="not synced",
    )


class GarminSource:
    """ActivitySource for Garmin Connect activity list (garth OAuth)."""

    source_id = "garmin"

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        raw = garmin_status(ctx)
        oauth = raw.get("oauth") or {}
        connected = bool(oauth.get("connected"))
        return ConnectionStatus(
            connected=connected,
            label="Garmin Connect",
            status_text="oauth connected" if connected else "oauth not connected",
            status_variant="success" if connected else "secondary",
        )

    async def fetch_page(
        self,
        ctx: UserContext,
        *,
        page: int = 1,
        per_page: int = 50,
        date_from: date | None = None,  # noqa: ARG002
        date_to: date | None = None,  # noqa: ARG002
    ) -> ActivityPage:
        if not garmin_resume(ctx):
            return ActivityPage(items=(), page=page, total_pages=1)
        start = (page - 1) * per_page
        batch = await asyncio.to_thread(
            list_garmin_activities,
            limit=per_page,
            start=start,
            ctx=ctx,
        )
        items = tuple(_item_to_normalized(item, ctx.user_id) for item in batch)
        has_next = len(batch) >= per_page
        total_pages = page + 1 if has_next else page
        return ActivityPage(
            items=items,
            page=page,
            total_pages=max(1, total_pages),
            total_items=None,
        )
