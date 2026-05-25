"""Phase 5b.0: bootstrap first admin and registration policy."""

from __future__ import annotations

import logging

from fit_sinc.config import Settings
from fit_sinc.state.store import Store

logger = logging.getLogger("fit_sinc.users.bootstrap")


def registration_is_open(settings: Settings | None = None) -> bool:
    """True when self-service /register is allowed (Phase 5b.3)."""
    if settings is None:
        from fit_sinc.config import get_settings

        settings = get_settings()
    return settings.registration_open


def apply_bootstrap_admin(store: Store, settings: Settings) -> None:
    """
    Ensure at least one admin exists.

    1. BOOTSTRAP_ADMIN_EMAIL — promote matching user (if found).
    2. If still no admins — promote default tenant (existing installs).
    """
    if settings.bootstrap_admin_email:
        email = settings.bootstrap_admin_email.strip().lower()
        user = store.get_user_by_email(email)
        if user:
            if not user.is_admin:
                store.set_admin(user.id, is_admin=True)
            logger.info("bootstrap admin: %s (BOOTSTRAP_ADMIN_EMAIL)", email)
        else:
            logger.warning(
                "bootstrap admin: user %s not found (BOOTSTRAP_ADMIN_EMAIL)",
                email,
            )

    if store.count_admins() > 0:
        return

    default_id = settings.default_user_id.strip() or "default"
    default = store.get_user(default_id)
    if default:
        store.set_admin(default.id, is_admin=True)
        logger.info("bootstrap admin: promoted tenant %s (no admins in DB)", default.id)
