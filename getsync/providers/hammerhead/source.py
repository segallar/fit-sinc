"""Hammerhead activity source adapter."""

from __future__ import annotations

from datetime import date
from typing import Any

from getsync.contracts.activities import ActivityPage, NormalizedActivity
from getsync.contracts.connections import ConnectionStatus
from getsync.hammerhead.client import HammerheadClient
from getsync.users.context import UserContext


def _hh_date(item: dict[str, Any]) -> str | None:
    return item.get("createdAt") or item.get("startDate") or item.get("date")


def _hh_total(payload: dict[str, Any], per_page: int, total_pages: int) -> int:
    for key in ("totalItems", "total", "totalCount", "totalElements"):
        value = payload.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    if total_pages > 0:
        data = payload.get("data") or []
        if total_pages == 1:
            return len(data)
        return (total_pages - 1) * per_page + len(data)
    return len(payload.get("data") or [])


def _item_to_normalized(item: dict[str, Any], user_id: str) -> NormalizedActivity | None:
    aid = str(item.get("id") or "")
    if not aid:
        return None
    return NormalizedActivity(
        user_id=user_id,
        source="hammerhead",
        activity_id=aid,
        name=str(item.get("name") or "—"),
        activity_date=_hh_date(item),
        distance=item.get("distance"),
        duration=item.get("duration"),
        activity_type="cycling",
        sync_status="not synced",
    )


class HammerheadSource:
    """ActivitySource + FIT download for Hammerhead Karoo cloud."""

    source_id = "hammerhead"

    def _client(self, ctx: UserContext) -> HammerheadClient:
        return HammerheadClient(ctx)

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        raw = self._client(ctx).status()
        connected = bool(raw.get("connected"))
        if connected:
            text = "connected"
            variant = "success"
        elif raw.get("reason") == "no tokens":
            text = "not connected"
            variant = "secondary"
        else:
            text = "token expired"
            variant = "warning"
        details: tuple[tuple[str, str], ...] = ()
        if raw.get("user_id"):
            details = (("Webhook user id", str(raw["user_id"])),)
        return ConnectionStatus(
            connected=connected,
            label="Hammerhead",
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
        date_to: date | None = None,  # noqa: ARG002
    ) -> ActivityPage:
        client = self._client(ctx)
        if client.load_tokens() is None:
            return ActivityPage(items=(), page=page, total_pages=1)
        start_date = date_from.isoformat() if date_from else None
        payload = await client.list_activities(
            page=page,
            per_page=per_page,
            start_date=start_date,
        )
        total_pages = max(1, int(payload.get("totalPages") or 1))
        total = _hh_total(payload, per_page, total_pages)
        items = tuple(
            row
            for item in payload.get("data") or []
            if (row := _item_to_normalized(item, ctx.user_id)) is not None
        )
        return ActivityPage(
            items=items,
            page=page,
            total_pages=total_pages,
            total_items=total,
        )

    async def fetch_metadata(
        self, ctx: UserContext, activity_id: str
    ) -> NormalizedActivity | None:
        data = await self._client(ctx).get_activity(activity_id)
        return NormalizedActivity(
            user_id=ctx.user_id,
            source="hammerhead",
            activity_id=activity_id,
            name=data.get("name"),
            activity_date=_hh_date(data),
            distance=data.get("distance"),
            duration=data.get("duration"),
            activity_type="cycling",
        )

    async def download_fit(self, ctx: UserContext, activity_id: str) -> bytes:
        return await self._client(ctx).download_fit(activity_id)
