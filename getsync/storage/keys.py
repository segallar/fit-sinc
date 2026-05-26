"""Logical object keys for activity artifacts (backend-agnostic)."""

from __future__ import annotations

import re

_SAFE_ID_RE = re.compile(r"[^a-zA-Z0-9._-]+")
_EXT = {"fit": ".fit", "gpx": ".gpx"}


def sanitize_external_id(external_id: str) -> str:
    """Safe single path segment for external_id."""
    cleaned = _SAFE_ID_RE.sub("_", (external_id or "unknown").strip())
    return cleaned[:200] or "unknown"


def build_object_key(
    source: str,
    external_id: str,
    *,
    kind: str = "fit",
) -> str:
    """
    Relative key under per-user prefix (no user_id).

    Example: activities/hammerhead/ride-42.fit
    Full S3 key later: {user_id}/{key}
    """
    suffix = _EXT.get(kind, f".{kind}" if not kind.startswith(".") else kind)
    safe = sanitize_external_id(external_id)
    src = sanitize_external_id(source)
    return f"activities/{src}/{safe}{suffix}"
