"""UTC storage; display and date filters use per-user IANA timezone."""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from getsync.users.timezones import DEFAULT_TIMEZONE, normalize_timezone

FMT = "%Y-%m-%d %H:%M"
FMT_DATE = "%d.%m.%Y"
FMT_TIME = "%H:%M:%S"


def zone_info(tz: str | None = None) -> ZoneInfo:
    return ZoneInfo(normalize_timezone(tz or ""))


def _parse_iso(iso: str, *, tz: str | None = None) -> datetime | None:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(zone_info(tz))
    except ValueError:
        return None


def now_in_tz(tz: str | None = None) -> str:
    return datetime.now(zone_info(tz)).strftime(FMT)


def format_iso(iso: str | None, *, tz: str | None = None) -> str:
    if not iso:
        return "—"
    dt = _parse_iso(iso, tz=tz)
    if dt is None:
        return iso
    return dt.strftime(FMT)


def format_datetime_parts(
    iso: str | None, *, tz: str | None = None
) -> tuple[str | None, str | None]:
    if not iso:
        return None, None
    dt = _parse_iso(iso, tz=tz)
    if dt is None:
        return iso, None
    return dt.strftime(FMT_DATE), dt.strftime(FMT_TIME)


def parse_date_only(value: str, *, tz: str | None = None) -> datetime | None:
    """Midnight on calendar day in the given timezone."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=zone_info(tz))
    except ValueError:
        return None


def format_ts(ts: float | None, *, tz: str | None = None) -> str:
    if not ts:
        return "—"
    return (
        datetime.fromtimestamp(ts, tz=timezone.utc)
        .astimezone(zone_info(tz))
        .strftime(FMT)
    )


def format_ttl(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    total = max(0, int(seconds))
    if total >= 86400:
        d, rem = divmod(total, 86400)
        h, _ = divmod(rem, 3600)
        return f"{d}d {h}h"
    if total >= 3600:
        h, rem = divmod(total, 3600)
        m, _ = divmod(rem, 60)
        return f"{h}h {m}m"
    m, s = divmod(total, 60)
    return f"{m}m {s}s"
