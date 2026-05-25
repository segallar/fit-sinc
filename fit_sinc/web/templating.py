"""Jinja2 templates for fit_sinc web UI."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from fit_sinc.timeutil import format_datetime_parts
from fit_sinc.users.timezones import options_for_select
from fit_sinc.web import html as H

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def timezone_options(selected: str | None = None) -> list[dict[str, object]]:
    return [
        {"group": group, "value": value, "selected": is_sel}
        for group, value, is_sel in options_for_select(selected)
    ]


def fmt_datetime_safe(iso: str | None) -> dict[str, str | None]:
    date_part, time_part = format_datetime_parts(iso)
    return {"iso": iso, "date": date_part, "time": time_part}


def pager_items(page: int, total_pages: int) -> list[int | str]:
    if total_pages <= 1:
        return []
    if total_pages <= 9:
        return list(range(1, total_pages + 1))
    pages: list[int | str] = [1]
    window = range(max(2, page - 2), min(total_pages, page + 2) + 1)
    if window.start > 2:
        pages.append("…")
    pages.extend(window)
    if window.stop < total_pages - 1:
        pages.append("…")
    pages.append(total_pages)
    return pages


def pager_query(params: dict[str, object], page: int) -> str:
    return H.query_string({**params, "page": page})


def jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals.update(
        esc=H.esc,
        fmt_date=H.fmt_date,
        fmt_datetime=H.fmt_datetime,
        fmt_datetime_safe=fmt_datetime_safe,
        fmt_now=H.fmt_now,
        fmt_km=H.fmt_km,
        fmt_duration=H.fmt_duration,
        fmt_duration_sec=H.fmt_duration_sec,
        fmt_ts=H.fmt_ts,
        fmt_ttl=H.fmt_ttl,
        query_string=H.query_string,
        timezone_options=timezone_options,
        pager_items=pager_items,
        pager_query=pager_query,
    )
    return env


def render_template(name: str, **context: object) -> str:
    return jinja_env().get_template(name).render(**context)
