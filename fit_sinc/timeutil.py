from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")
FMT = "%Y-%m-%d %H:%M MSK"
FMT_DATE = "%d.%m.%Y"
FMT_TIME = "%H:%M:%S"


def _parse_iso(iso: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MSK)
    except ValueError:
        return None


def now_msk() -> str:
    return datetime.now(MSK).strftime(FMT)


def format_iso(iso: str | None) -> str:
    if not iso:
        return "—"
    dt = _parse_iso(iso)
    if dt is None:
        return iso
    return dt.strftime(FMT)


def format_datetime_parts(iso: str | None) -> tuple[str | None, str | None]:
    if not iso:
        return None, None
    dt = _parse_iso(iso)
    if dt is None:
        return iso, None
    return dt.strftime(FMT_DATE), dt.strftime(FMT_TIME)


def parse_date_only(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=MSK)
    except ValueError:
        return None


def format_ts(ts: float | None) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(MSK).strftime(FMT)


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
