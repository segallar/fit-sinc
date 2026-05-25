"""IANA timezones for user profile (select + validation)."""

from __future__ import annotations

from zoneinfo import ZoneInfo, available_timezones

DEFAULT_TIMEZONE = "Europe/Moscow"

# Curated groups for HTML <select> (not full 600+ IANA list).
TIMEZONE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "UTC",
        ("UTC",),
    ),
    (
        "Europe",
        (
            "Europe/Moscow",
            "Europe/Kaliningrad",
            "Europe/Samara",
            "Europe/Yekaterinburg",
            "Europe/Omsk",
            "Europe/Krasnoyarsk",
            "Europe/Irkutsk",
            "Europe/Yakutsk",
            "Europe/Vladivostok",
            "Europe/Magadan",
            "Europe/Kamchatka",
            "Europe/London",
            "Europe/Dublin",
            "Europe/Lisbon",
            "Europe/Berlin",
            "Europe/Paris",
            "Europe/Rome",
            "Europe/Madrid",
            "Europe/Amsterdam",
            "Europe/Brussels",
            "Europe/Vienna",
            "Europe/Warsaw",
            "Europe/Prague",
            "Europe/Budapest",
            "Europe/Bucharest",
            "Europe/Helsinki",
            "Europe/Athens",
            "Europe/Istanbul",
            "Europe/Kyiv",
            "Europe/Zurich",
            "Europe/Stockholm",
            "Europe/Oslo",
            "Europe/Copenhagen",
        ),
    ),
    (
        "Asia",
        (
            "Asia/Dubai",
            "Asia/Tbilisi",
            "Asia/Yerevan",
            "Asia/Baku",
            "Asia/Almaty",
            "Asia/Tashkent",
            "Asia/Kolkata",
            "Asia/Bangkok",
            "Asia/Singapore",
            "Asia/Hong_Kong",
            "Asia/Shanghai",
            "Asia/Tokyo",
            "Asia/Seoul",
        ),
    ),
    (
        "Americas",
        (
            "America/New_York",
            "America/Chicago",
            "America/Denver",
            "America/Phoenix",
            "America/Los_Angeles",
            "America/Anchorage",
            "America/Toronto",
            "America/Vancouver",
            "America/Mexico_City",
            "America/Sao_Paulo",
            "America/Buenos_Aires",
            "America/Santiago",
        ),
    ),
    (
        "Pacific & Australia",
        (
            "Pacific/Auckland",
            "Australia/Sydney",
            "Australia/Melbourne",
            "Australia/Perth",
            "Pacific/Honolulu",
        ),
    ),
)

_IANA: frozenset[str] = frozenset(available_timezones())

_CHOICES: tuple[str, ...] = tuple(
    tz for _label, zones in TIMEZONE_GROUPS for tz in zones
)


def timezone_choices() -> tuple[str, ...]:
    """Flat list for selects and CLI hints."""
    return _CHOICES


def is_valid_timezone(name: str) -> bool:
    tz = (name or "").strip()
    if not tz:
        return False
    if tz in _IANA:
        return True
    try:
        ZoneInfo(tz)
        return True
    except Exception:
        return False


def normalize_timezone(name: str, *, default: str = DEFAULT_TIMEZONE) -> str:
    """Return validated IANA id or raise ValueError."""
    tz = (name or "").strip() or default
    if not is_valid_timezone(tz):
        raise ValueError(
            f"Unknown timezone {tz!r}. Choose from the list, e.g. {DEFAULT_TIMEZONE}."
        )
    return tz


def options_for_select(selected: str | None = None) -> list[tuple[str, str, bool]]:
    """
    Options for <select>: (group_label, value, is_selected).
    group_label '' = orphan option (custom legacy value).
    """
    sel = (selected or DEFAULT_TIMEZONE).strip()
    seen: set[str] = set()
    out: list[tuple[str, str, bool]] = []

    if sel and sel not in _CHOICES and is_valid_timezone(sel):
        out.append(("", sel, True))
        seen.add(sel)

    for group, zones in TIMEZONE_GROUPS:
        for tz in zones:
            if tz in seen:
                continue
            seen.add(tz)
            out.append((group, tz, tz == sel))

    if sel and sel not in seen and is_valid_timezone(sel):
        out.append(("", sel, True))

    return out
