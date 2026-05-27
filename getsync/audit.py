"""Admin audit trail (SQLite admin_audit_events + getsync.audit logger)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Request

from getsync import __version__
from getsync.build_info import deploy_number, deployed_at_iso, git_commit_short
from getsync.state.store import Store

_STATE_FILE = "app_audit_state.json"


def log(
    store: Store,
    event_type: str,
    message: str = "",
    *,
    user_id: str | None = None,
    subject: str | None = None,
    actor_user_id: str | None = None,
) -> None:
    store.log_admin_audit(
        event_type,
        message,
        user_id=user_id,
        subject=subject,
        actor_user_id=actor_user_id,
    )


def request_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "?"


def record_startup(store: Store, data_dir: Path) -> None:
    """Log process start; log deploy when commit or deploy # changed since last run."""
    commit = git_commit_short()
    num = deploy_number()
    deployed = deployed_at_iso()

    parts = [f"v{__version__}"]
    if commit != "dev":
        parts.append(commit)
    if num is not None:
        parts.append(f"deploy #{num}")
    if deployed:
        parts.append(deployed)
    log(
        store,
        "app_started",
        " · ".join(parts),
        subject=commit if commit != "dev" else "system",
    )

    state_path = data_dir / _STATE_FILE
    prev = _load_state(state_path)
    current_commit = commit if commit != "dev" else None
    changed = prev is not None and (
        prev.get("deploy_number") != num or prev.get("commit") != current_commit
    )
    if changed:
        msg_parts: list[str] = []
        if num is not None:
            msg_parts.append(f"deploy #{num}")
        if current_commit:
            msg_parts.append(f"commit {current_commit}")
        old_parts: list[str] = []
        if prev.get("deploy_number") is not None:
            old_parts.append(f"#{prev['deploy_number']}")
        if prev.get("commit"):
            old_parts.append(str(prev["commit"]))
        if old_parts:
            msg_parts.append(f"(was {' · '.join(old_parts)})")
        log(
            store,
            "deploy",
            " ".join(msg_parts),
            subject=str(num) if num is not None else (current_commit or "deploy"),
        )

    _save_state(
        state_path,
        {"deploy_number": num, "commit": current_commit},
    )


def _load_state(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _save_state(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=0) + "\n", encoding="utf-8")
