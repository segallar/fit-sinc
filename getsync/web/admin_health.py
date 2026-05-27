"""Admin App Health page context."""

from __future__ import annotations

from getsync.config import Settings
from getsync.ops.app_health import build_admin_health_context
from getsync.state.store import Store
from getsync.web.templating import render_template


def admin_health_context(settings: Settings, store: Store) -> dict[str, object]:
    return build_admin_health_context(settings, store)


def render_admin_health_panel(settings: Settings, store: Store) -> str:
    return render_template(
        "components/admin_health_panel.html",
        **admin_health_context(settings, store),
    )
