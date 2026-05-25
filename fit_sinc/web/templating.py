"""Jinja2 UI v2 — параллельно html.py, без миграции существующих страниц."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from fit_sinc.web import html as H

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def jinja_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(_TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals.update(
        esc=H.esc,
        fmt_date=H.fmt_date,
        fmt_datetime=H.fmt_datetime,
        fmt_now=H.fmt_now,
        fmt_km=H.fmt_km,
        fmt_duration=H.fmt_duration,
        fmt_duration_sec=H.fmt_duration_sec,
        fmt_ts=H.fmt_ts,
        fmt_ttl=H.fmt_ttl,
        query_string=H.query_string,
        render_pager=H.render_pager,
    )
    return env


def render_template(name: str, **context: object) -> str:
    return jinja_env().get_template(name).render(**context)
