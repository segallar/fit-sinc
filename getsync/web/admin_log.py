"""Unified admin log (sync, Garmin JWT, admin audit)."""

from __future__ import annotations

from getsync.state.store import AdminLogRow, Store
from getsync.web.auth import APP_ADMIN_PREFIX
from getsync.web.connections import _session_event_class
from getsync.web.templating import render_template

def _event_status_class(log_kind: str, event_type: str) -> str:
    if log_kind == "garmin":
        return _session_event_class(event_type)
    if log_kind == "admin":
        if event_type in (
            "user_created",
            "user_registered",
            "user_login",
            "deploy",
            "settings_hammerhead_connected",
            "settings_garmin_connected",
        ):
            return "ok"
        if event_type in ("user_logout", "settings_hammerhead_disconnected", "settings_garmin_disconnected"):
            return ""
        return ""
    if event_type == "error":
        return "failed"
    if event_type in ("garmin_uploaded", "garmin_duplicate", "synced", "fit_saved"):
        return "ok"
    return ""


def _kind_label(log_kind: str) -> str:
    if log_kind == "garmin":
        return "Garmin JWT"
    if log_kind == "admin":
        return "Admin"
    return "Sync"


def admin_log_context(
    store: Store,
    *,
    user_id: str | None,
    log_page: int,
    pager_path: str,
    per_page: int = 50,
) -> dict[str, object]:
    total = store.count_admin_log(user_id=user_id)
    offset = (log_page - 1) * per_page
    rows = store.list_admin_log(limit=per_page, offset=offset, user_id=user_id)
    users_by_id = {u.id: u for u in store.list_users()}
    has_next = offset + len(rows) < total
    from_idx = offset + 1 if total else 0
    to_idx = offset + len(rows)

    def _page_href(page: int) -> str:
        return f"{pager_path}?log_page={page}#admin-log"

    events = [_row_view(r, users_by_id) for r in rows]

    return {
        "log_events": events,
        "log_page": log_page,
        "log_prev_href": _page_href(log_page - 1) if log_page > 1 else None,
        "log_next_href": _page_href(log_page + 1) if has_next else None,
        "log_range_label": f"{from_idx}–{to_idx} of {total}",
        "show_user_column": user_id is None,
    }


def _row_view(row: AdminLogRow, users_by_id: dict) -> dict[str, object]:
    uid = row.user_id
    if uid and uid in users_by_id:
        user_label = users_by_id[uid].slug
    else:
        user_label = uid or "—"
    subject = row.subject or "—"
    subject_title = subject
    return {
        "created_at": row.created_at,
        "user_id": uid,
        "user_label": user_label,
        "kind_label": _kind_label(row.log_kind),
        "log_kind": row.log_kind,
        "event_type": row.event_type,
        "subject": subject,
        "subject_title": subject_title,
        "message": row.message or "",
        "status_class": _event_status_class(row.log_kind, row.event_type),
    }


def render_admin_log_table(
    store: Store,
    *,
    log_page: int,
    user_id: str | None = None,
    pager_path: str | None = None,
) -> str:
    """HTML fragment for HTMX poll or full page include."""
    path = pager_path or f"{APP_ADMIN_PREFIX}/log"
    return render_template(
        "components/admin_log_table.html",
        admin_prefix=APP_ADMIN_PREFIX,
        **admin_log_context(
            store,
            user_id=user_id,
            log_page=log_page,
            pager_path=path,
        ),
    )
