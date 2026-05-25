import html
from urllib.parse import urlencode

from fit_sinc.timeutil import format_datetime_parts, format_iso, format_ts, format_ttl, now_msk


BASE_CSS = """
  body { font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; }
  body.wide { max-width: 1280px; }
  .hero { display: flex; align-items: center; gap: 0.85rem; margin-bottom: 0.5rem; }
  .hero img { border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
  .hero h1 { margin: 0; }
  nav { margin: 1rem 0 1.5rem; display: flex; gap: 1rem; flex-wrap: wrap; }
  nav a { color: #0f766e; text-decoration: none; }
  nav a:hover { text-decoration: underline; }
  .ok { color: #0a0; } .warn { color: #a60; } .err { color: #c00; }
  code, .mono { font-family: ui-monospace, monospace; background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.95rem; }
  th, td { padding: 0.45rem 0.5rem; border-bottom: 1px solid #eee; vertical-align: top; text-align: left; }
  th { color: #666; font-weight: 600; }
  .btn { display: inline-block; padding: 0.25rem 0.6rem; border: 1px solid #ccc; border-radius: 6px;
         background: #fafafa; color: #222; text-decoration: none; font-size: 0.85rem; cursor: pointer; }
  .btn:hover { background: #eee; }
  form.inline { display: inline; margin: 0; }
  .status-synced { color: #0a0; } .status-error { color: #c00; }
  .status-pending { color: #a60; } .status-skipped { color: #888; }
  .status-ok { color: #0a0; } .status-failed { color: #c00; } .status-warn { color: #a60; }
  .panel { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem 1.25rem; margin: 1rem 0; }
  .tabs { display: flex; gap: 0.5rem; margin: 1rem 0; }
  .tabs a { padding: 0.4rem 0.9rem; border: 1px solid #ccc; border-radius: 999px; text-decoration: none; color: #333; }
  .tabs a.active { background: #0f766e; border-color: #0f766e; color: #fff; font-weight: 600; }
  .tabs a:hover:not(.active) { background: #f3f4f6; }
  .status-not-synced { color: #888; }
  .pager { display: flex; gap: 0.75rem; align-items: center; margin-top: 1rem; flex-wrap: wrap; }
  .pager-pages { display: flex; gap: 0.35rem; flex-wrap: wrap; align-items: center; }
  .pager-pages a, .pager-pages span.page-current, .pager-pages span.page-gap {
    display: inline-block; min-width: 2rem; text-align: center; padding: 0.25rem 0.55rem;
    border: 1px solid #ddd; border-radius: 6px; text-decoration: none; color: #333; font-size: 0.85rem;
  }
  .pager-pages a:hover { background: #f3f4f6; }
  .pager-pages span.page-current { background: #0f766e; border-color: #0f766e; color: #fff; font-weight: 600; }
  .pager-pages span.page-gap { border: none; min-width: auto; color: #888; }
  .filters { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 0.75rem 1rem;
             align-items: end; margin: 1rem 0; padding: 1rem; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 8px; }
  .filters label { display: flex; flex-direction: column; gap: 0.25rem; font-size: 0.85rem; color: #555; }
  .filters input, .filters select { padding: 0.35rem 0.5rem; border: 1px solid #ccc; border-radius: 6px; font: inherit; }
  .filters-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }
  .dt { white-space: nowrap; font-variant-numeric: tabular-nums; }
  .dt-date { display: block; font-weight: 500; }
  .dt-time { display: block; font-size: 0.85em; color: #666; }
  .table-wrap { overflow-x: auto; }
"""


def esc(value: object) -> str:
    if value is None:
        return "—"
    return html.escape(str(value))


def fmt_date(iso: str | None) -> str:
    return format_iso(iso)


def fmt_datetime(iso: str | None) -> str:
    date_part, time_part = format_datetime_parts(iso)
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


def query_string(params: dict[str, object]) -> str:
    clean = {k: v for k, v in params.items() if v not in (None, "", [])}
    return urlencode(clean)


def render_pager(
    base_path: str,
    params: dict[str, object],
    *,
    page: int,
    total_pages: int,
) -> str:
    if total_pages <= 1:
        return ""

    def link(p: int, label: str | None = None) -> str:
        q = query_string({**params, "page": p})
        text = esc(label if label is not None else str(p))
        return f'<a href="{esc(base_path)}?{q}">{text}</a>'

    pages: list[int | str] = []
    if total_pages <= 9:
        pages = list(range(1, total_pages + 1))
    else:
        pages.append(1)
        window = range(max(2, page - 2), min(total_pages, page + 2) + 1)
        if window.start > 2:
            pages.append("…")
        pages.extend(window)
        if window.stop < total_pages - 1:
            pages.append("…")
        pages.append(total_pages)

    parts: list[str] = []
    if page > 1:
        parts.append(link(page - 1, "←"))
    for item in pages:
        if item == "…":
            parts.append('<span class="page-gap">…</span>')
        elif item == page:
            parts.append(f'<span class="page-current">{page}</span>')
        else:
            parts.append(link(int(item)))
    if page < total_pages:
        parts.append(link(page + 1, "→"))
    return f'<div class="pager-pages">{"".join(parts)}</div>'


def fmt_now() -> str:
    return now_msk()


def fmt_km(distance: float | None) -> str:
    if distance is None:
        return "—"
    # Hammerhead API: distance in meters
    km = distance / 1000.0
    return f"{km:.1f} km"


def fmt_duration(duration: float | None) -> str:
    if duration is None:
        return "—"
    # Hammerhead API: duration in milliseconds
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


def fmt_ts(ts: float | None) -> str:
    return format_ts(ts)


def fmt_ttl(seconds: float | None) -> str:
    return format_ttl(seconds)


def page(title: str, body: str, *, active: str = "", wide: bool = False) -> str:
    nav = [
        ("", "Dashboard"),
        ("/activities", "Activities"),
        ("/log", "Sync log"),
        ("/session", "Garmin session"),
    ]
    links = []
    for href, label in nav:
        cls = ' style="font-weight:600"' if (href == active or (active == "/" and href == "")) else ""
        path = href or "/"
        links.append(f'<a href="{path}"{cls}>{esc(label)}</a>')
    body_class = "wide" if wide else ""
    body_attr = f' class="{body_class}"' if body_class else ""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} — fit_sinc</title>
  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
  <style>{BASE_CSS}</style>
</head>
<body{body_attr}>
  <header class="hero">
    <img src="/static/icon.svg" alt="fit_sinc" width="48" height="48">
    <h1>fit_sinc</h1>
  </header>
  <nav>{"".join(links)}</nav>
  {body}
</body>
</html>"""
