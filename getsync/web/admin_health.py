"""Admin App Health page context."""

from __future__ import annotations

from getsync.config import Settings
from getsync.ops.app_health import build_admin_health_context
from getsync.state.store import Store


def admin_health_context(settings: Settings, store: Store) -> dict[str, object]:
    return build_admin_health_context(settings, store)
