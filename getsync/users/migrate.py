"""Bootstrap helpers for default user."""

from __future__ import annotations

from getsync.config import Settings
from getsync.storage import load_json


def infer_hammerhead_user_id(settings: Settings) -> str | None:
    """Read Hammerhead user id from default tenant tokens file."""
    path = settings.data_dir / "users" / settings.default_user_id / "hammerhead_tokens.json"
    data = load_json(path)
    if not data:
        return None
    uid = data.get("user_id")
    return str(uid) if uid else None
