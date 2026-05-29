"""Strava API payloads → NormalizedActivity."""

from __future__ import annotations

from typing import Any

from getsync.contracts.activities import NormalizedActivity


def strava_activity_date(item: dict[str, Any]) -> str | None:
    raw = item.get("start_date_local") or item.get("start_date")
    if raw is None:
        return None
    return str(raw)


def item_to_normalized(item: dict[str, Any], user_id: str) -> NormalizedActivity | None:
    aid = item.get("id")
    if aid is None:
        return None
    activity_type = item.get("sport_type") or item.get("type")
    return NormalizedActivity(
        user_id=user_id,
        source="strava",
        activity_id=str(aid),
        name=str(item.get("name") or "—"),
        activity_date=strava_activity_date(item),
        distance=_float_or_none(item.get("distance")),
        duration=_float_or_none(item.get("moving_time")),
        activity_type=str(activity_type) if activity_type else None,
        sync_status="not synced",
    )


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
