"""Garmin per-user credentials (2.16.1)."""

from __future__ import annotations

from typing import Any

from getsync.credentials.store import PROVIDER_GARMIN, CredentialStore
from getsync.users.context import UserContext, as_context

META_EMAIL = "email"
META_STORE_PASSWORD = "store_password_for_auto_login"


def get_garmin_meta(ctx: UserContext | None = None) -> dict[str, Any]:
    return CredentialStore(ctx).load_meta(PROVIDER_GARMIN)


def save_garmin_login(
    ctx: UserContext | None,
    email: str,
    password: str | None,
    *,
    store_password: bool,
) -> None:
    """Persist email in meta; password in secrets.enc when store_password=True."""
    user_ctx = as_context(ctx)
    store = CredentialStore(user_ctx)
    email = email.strip()
    store.save_meta(
        PROVIDER_GARMIN,
        {
            META_EMAIL: email,
            META_STORE_PASSWORD: bool(store_password),
        },
    )
    if not store_password:
        if store.has_stored_secrets(PROVIDER_GARMIN):
            secrets = store.load_secrets(PROVIDER_GARMIN)
            secrets.pop("password", None)
            if secrets:
                store.save_secrets(PROVIDER_GARMIN, secrets)
            else:
                store.secrets_path(PROVIDER_GARMIN).unlink(missing_ok=True)
        return
    if not password:
        return
    store.save_secrets(
        PROVIDER_GARMIN,
        {"email": email, "password": password},
    )


def load_garmin_login(ctx: UserContext | None = None) -> tuple[str, str] | None:
    """Return (email, password) when auto-login is enabled and secrets exist."""
    user_ctx = as_context(ctx)
    store = CredentialStore(user_ctx)
    meta = store.load_meta(PROVIDER_GARMIN)
    if not meta.get(META_STORE_PASSWORD):
        return None
    email = (meta.get(META_EMAIL) or "").strip()
    if not email:
        return None
    if not store.has_stored_secrets(PROVIDER_GARMIN):
        return None
    try:
        secrets = store.load_secrets(PROVIDER_GARMIN)
    except Exception:
        return None
    password = secrets.get("password")
    if not email or not password:
        return None
    return email, str(password)


def clear_garmin_credentials(ctx: UserContext | None = None) -> None:
    CredentialStore(ctx).clear(PROVIDER_GARMIN)


def garmin_auto_login_configured(ctx: UserContext | None = None) -> bool:
    return load_garmin_login(ctx) is not None
