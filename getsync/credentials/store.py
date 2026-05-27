"""Encrypted secrets per user and provider (Fernet)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from getsync.config import get_settings
from getsync.users.context import UserContext, as_context

logger = logging.getLogger("getsync.credentials")

PROVIDER_HAMMERHEAD = "hammerhead"
PROVIDER_GARMIN = "garmin"


class CredentialStoreError(RuntimeError):
    pass


class CredentialStore:
    """`data/users/{id}/connections/{provider}/meta.json` + `secrets.enc`."""

    def __init__(self, ctx: UserContext | None = None) -> None:
        self._ctx = as_context(ctx)

    @property
    def user_id(self) -> str:
        return self._ctx.user_id

    def connection_dir(self, provider: str) -> Path:
        return self._ctx.user_data_dir / "connections" / provider

    def meta_path(self, provider: str) -> Path:
        return self.connection_dir(provider) / "meta.json"

    def secrets_path(self, provider: str) -> Path:
        return self.connection_dir(provider) / "secrets.enc"

    def load_meta(self, provider: str) -> dict[str, Any]:
        path = self.meta_path(provider)
        if not path.is_file():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Invalid meta %s: %s", path, exc)
            return {}
        return data if isinstance(data, dict) else {}

    def save_meta(self, provider: str, meta: dict[str, Any]) -> None:
        path = self.meta_path(provider)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def load_secrets(self, provider: str) -> dict[str, Any]:
        path = self.secrets_path(provider)
        if not path.is_file():
            return {}
        key = _fernet_key()
        if key is None:
            raise CredentialStoreError(
                "GETSYNC_SECRETS_KEY is not set — cannot read stored credentials"
            )
        try:
            raw = Fernet(key).decrypt(path.read_bytes())
        except InvalidToken as exc:
            raise CredentialStoreError(
                "Cannot decrypt secrets (wrong GETSYNC_SECRETS_KEY?)"
            ) from exc
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def save_secrets(self, provider: str, secrets: dict[str, Any]) -> None:
        key = _fernet_key()
        if key is None:
            raise CredentialStoreError(
                "GETSYNC_SECRETS_KEY is not set — cannot store credentials. "
                "Generate: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        path = self.secrets_path(provider)
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = json.dumps(secrets, ensure_ascii=False).encode("utf-8")
        path.write_bytes(Fernet(key).encrypt(blob))

    def clear(self, provider: str) -> None:
        root = self.connection_dir(provider)
        if root.is_dir():
            import shutil

            shutil.rmtree(root)

    def has_stored_secrets(self, provider: str) -> bool:
        return self.secrets_path(provider).is_file()


def _fernet_key() -> bytes | None:
    raw = get_settings().getsync_secrets_key.strip()
    if not raw:
        return None
    return raw.encode("utf-8")
