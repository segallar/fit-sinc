"""Sync event log context for admin UI."""

from __future__ import annotations

from getsync.state.store import Store


def sync_log_context(
    store: Store,
    *,
    user_id: str | None,
    log_page: int,
    pager_path: str,
    per_page: int = 50,
) -> dict[str, object]:
    """Build template context for sync_log_section (per-user or all tenants)."""
    total = store.count_events(user_id=user_id)
    offset = (log_page - 1) * per_page
    events = store.list_events(limit=per_page, offset=offset, user_id=user_id)
    has_next = offset + len(events) < total
    from_idx = offset + 1 if total else 0
    to_idx = offset + len(events)

    def _page_href(page: int) -> str:
        return f"{pager_path}?log_page={page}#sync-log"

    return {
        "log_events": events,
        "log_page": log_page,
        "log_prev_href": _page_href(log_page - 1) if log_page > 1 else None,
        "log_next_href": _page_href(log_page + 1) if has_next else None,
        "log_range_label": f"{from_idx}–{to_idx} of {total}",
        "show_user_column": user_id is None,
        "sync_log_compact": True,
    }
