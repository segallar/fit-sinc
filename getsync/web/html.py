import html
from dataclasses import dataclass
from urllib.parse import urlencode

from getsync.timeutil import (
    format_datetime_parts,
    format_iso,
    format_ts,
    format_ttl,
    now_in_tz,
)
from getsync.users.timezones import DEFAULT_TIMEZONE, normalize_timezone


def esc(value: object) -> str:
    if value is None:
        return "—"
    return html.escape(str(value))


@dataclass(frozen=True)
class DateFormatter:
    """Format dates in a single IANA timezone (typically users.timezone)."""

    tz: str = DEFAULT_TIMEZONE

    def __post_init__(self) -> None:
        object.__setattr__(self, "tz", normalize_timezone(self.tz))

    def fmt_date(self, iso: str | None) -> str:
        return format_iso(iso, tz=self.tz)

    def fmt_datetime(self, iso: str | None) -> str:
        date_part, time_part = format_datetime_parts(iso, tz=self.tz)
        if not date_part:
            return "—"
        if not time_part:
            return esc(date_part)
        iso_attr = esc(iso or "")
        return (
            f'<time class="dt" datetime="{iso_attr}">'
            f'<span class="dt-date">{esc(date_part)}</span>'
            f'<span class="dt-time">{esc(time_part)}</span>'
            f"</time>"
        )

    def fmt_now(self) -> str:
        return now_in_tz(self.tz)

    def fmt_ts(self, ts: float | None) -> str:
        return format_ts(ts, tz=self.tz)

    def datetime_parts(self, iso: str | None) -> dict[str, str | None]:
        date_part, time_part = format_datetime_parts(iso, tz=self.tz)
        return {"iso": iso, "date": date_part, "time": time_part}


def make_formatter(tz: str | None = None) -> DateFormatter:
    return DateFormatter(tz=tz or DEFAULT_TIMEZONE)


def query_string(params: dict[str, object]) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "", [])}
    return urlencode(clean)


def fmt_km(distance: float | None) -> str:
    if distance is None:
        return "—"
    km = distance / 1000.0
    return f"{km:.1f} km"


def fmt_duration(duration: float | None) -> str:
    if duration is None:
        return "—"
    total = int(duration / 1000)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


def fmt_duration_sec(duration: float | None) -> str:
    if duration is None:
        return "—"
    total = int(duration)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


def fmt_ttl(seconds: float | None) -> str:
    return format_ttl(seconds)
