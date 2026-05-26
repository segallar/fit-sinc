"""Jinja2 templates for GetSync web UI."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from getsync import __version__
from getsync.build_info import deploy_number, deploy_time_footer, git_commit_short
from getsync.users.locale import options_for_select as locale_options_for_select
from getsync.users.timezones import DEFAULT_TIMEZONE, options_for_select
from getsync.web import html as H
from getsync.web.site_i18n import landing_lang_options as site_lang_options_for_select

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def landing_lang_options(selected: str | None = None) -> list[dict[str, object]]:
    return [
        {"label": label, "value": value, "selected": is_sel}
        for label, value, is_sel in site_lang_options_for_select(selected)
    ]


def locale_options(selected: str | None = None) -> list[dict[str, object]]:
    return [
        {"label": label, "value": value, "selected": is_sel}
        for label, value, is_sel in locale_options_for_select(selected)
    ]


def timezone_options(selected: str | None = None) -> list[dict[str, object]]:
    return [
        {"group": group, "value": value, "selected": is_sel}
        for group, value, is_sel in options_for_select(selected)
    ]


def formatter_globals(tz: str | None = None) -> dict[str, object]:
    f = H.make_formatter(tz)
    return {
        "fmt_date": f.fmt_date,
        "fmt_datetime": f.fmt_datetime,
        "fmt_datetime_safe": f.datetime_parts,
        "fmt_now": f.fmt_now,
        "fmt_ts": f.fmt_ts,
    }


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
    env.filters["urlencode_path"] = lambda s: quote(str(s), safe="")
    defaults = formatter_globals(DEFAULT_TIMEZONE)
    env.globals.update(
        app_version=__version__,
        git_commit=git_commit_short(),
        deploy_number=deploy_number(),
        deploy_time=deploy_time_footer(),
        esc=H.esc,
        fmt_km=H.fmt_km,
        fmt_duration=H.fmt_duration,
        fmt_duration_sec=H.fmt_duration_sec,
        fmt_ttl=H.fmt_ttl,
        query_string=H.query_string,
        locale_options=locale_options,
        landing_lang_options=landing_lang_options,
        timezone_options=timezone_options,
        pager_items=pager_items,
        pager_query=pager_query,
        **defaults,
    )
    return env


def render_template(
    name: str,
    *,
    display_timezone: str | None = None,
    **context: object,
) -> str:
    tz = display_timezone if display_timezone is not None else DEFAULT_TIMEZONE
    return jinja_env().get_template(name).render(
        **formatter_globals(tz),
        **context,
    )
