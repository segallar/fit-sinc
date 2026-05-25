"""List activities from Garmin Connect via garth OAuth."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import garth

from fit_sinc.garmin.session import garmin_resume
from fit_sinc.users.context import UserContext, as_context


@dataclass(frozen=True)
class GarminActivityItem:
    activity_id: int
    name: str
    activity_date: str | None
    distance: float | None
    duration: float | None
    activity_type: str | None


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.isoformat()
    return dt.astimezone().isoformat()


def list_garmin_activities(
    *,
    limit: int = 50,
    start: int = 0,
    ctx: UserContext | None = None,
) -> list[GarminActivityItem]:
    user_ctx = as_context(ctx)
    if not garmin_resume(user_ctx):
        raise RuntimeError("Garmin OAuth not connected — run: fit_sinc garmin login")

    from garth.data.activity import Activity

    items = Activity.list(limit=limit, start=start)
    out: list[GarminActivityItem] = []
    for item in items:
        type_key = None
        if item.activity_type:
            type_key = item.activity_type.type_key
        out.append(
            GarminActivityItem(
                activity_id=int(item.activity_id),
                name=item.activity_name or "—",
                activity_date=_iso(item.start_time_local or item.start_time_gmt),
                distance=item.distance or (item.summary.distance if item.summary else None),
                duration=item.duration or (item.summary.duration if item.summary else None),
                activity_type=type_key,
            )
        )
    return out
