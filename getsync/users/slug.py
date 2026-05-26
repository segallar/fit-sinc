"""Slug generation for new users (registration, CLI)."""

from __future__ import annotations

import re

from getsync.state.store import Store

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,62}$")
_EMAIL_LOCAL_RE = re.compile(r"[^a-z0-9]+")


def normalize_slug_base(value: str) -> str:
    """Turn arbitrary text into a valid slug base (may need length / uniqueness fix)."""
    s = value.strip().lower()
    s = _EMAIL_LOCAL_RE.sub("_", s)
    s = s.strip("_")
    if not s or not s[0].isalnum():
        s = f"user_{s}" if s else "user"
    if len(s) < 2:
        s = f"{s}_1"
    return s[:63]


def slug_from_email(email: str) -> str:
    local = email.strip().lower().split("@", 1)[0]
    return normalize_slug_base(local)


def is_valid_slug(slug: str) -> bool:
    return bool(_SLUG_RE.match(slug.strip().lower()))


def allocate_unique_slug(store: Store, base: str) -> str:
    """Return base or base-2, base-3, … until unused as users.id."""
    candidate = normalize_slug_base(base)
    if not store.get_user(candidate):
        return candidate
    for n in range(2, 10_000):
        suffix = f"-{n}"
        stem = candidate[: 63 - len(suffix)] + suffix
        if not store.get_user(stem):
            return stem
    raise RuntimeError("could not allocate unique slug")
