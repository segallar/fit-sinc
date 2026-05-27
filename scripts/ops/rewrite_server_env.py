#!/usr/bin/env python3
"""Rewrite /opt/getsync/.env: drop legacy keys, keep values. Run on server as root."""
from __future__ import annotations

import os
import pwd
from datetime import datetime, timezone
from pathlib import Path

ENV_PATH = Path(os.environ.get("GETSYNC_ENV_PATH", "/opt/getsync/.env"))

LEGACY_KEYS = frozenset({"ADMIN_PASSWORD", "GARMIN_EMAIL", "GARMIN_PASSWORD"})


def parse_dotenv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        out[key.strip()] = value
    return out


def build_env(env: dict[str, str]) -> str:
    def g(key: str, default: str = "") -> str:
        return env.get(key, default)

    lines = [
        "# /opt/getsync/.env — не в git",
        "",
        "# Hammerhead OAuth",
        f"HAMMERHEAD_CLIENT_ID={g('HAMMERHEAD_CLIENT_ID')}",
        f"HAMMERHEAD_CLIENT_SECRET={g('HAMMERHEAD_CLIENT_SECRET')}",
        f"HAMMERHEAD_WEBHOOK_SECRET={g('HAMMERHEAD_WEBHOOK_SECRET')}",
        f"HAMMERHEAD_REDIRECT_URI={g('HAMMERHEAD_REDIRECT_URI', 'http://127.0.0.1:8765/callback')}",
        f"HAMMERHEAD_WEB_REDIRECT_URI={g('HAMMERHEAD_WEB_REDIRECT_URI')}",
        f"HAMMERHEAD_SCOPE={g('HAMMERHEAD_SCOPE', 'activity:read')}",
        "",
        f"GETSYNC_SECRETS_KEY={g('GETSYNC_SECRETS_KEY')}",
        "",
        f"DATA_DIR={g('DATA_DIR', 'data')}",
        "",
        f"SESSION_SECRET={g('SESSION_SECRET')}",
        f"SESSION_COOKIE_SECURE={g('SESSION_COOKIE_SECURE', 'true')}",
        "",
        f"REGISTRATION_OPEN={g('REGISTRATION_OPEN', 'false')}",
        "",
        "# Garmin Connect — только per-user (Settings / CLI), не GARMIN_* в .env",
        "",
        "# Почта (Resend)",
        f"MAIL_BACKEND={g('MAIL_BACKEND', 'null')}",
        f"RESEND_API_KEY={g('RESEND_API_KEY')}",
        f'MAIL_FROM={g("MAIL_FROM", "GetSync <noreply@getsync.me>")}',
        f"MAIL_REPLY_TO={g('MAIL_REPLY_TO')}",
        f"APP_PUBLIC_URL={g('APP_PUBLIC_URL', 'https://app.getsync.me')}",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    raw = ENV_PATH.read_text(encoding="utf-8")
    env = parse_dotenv(raw)
    removed = [k for k in LEGACY_KEYS if k in env]
    for k in LEGACY_KEYS:
        env.pop(k, None)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = ENV_PATH.with_name(f".env.bak-{stamp}")
    backup.write_text(raw, encoding="utf-8")
    backup.chmod(0o600)

    ENV_PATH.write_text(build_env(env), encoding="utf-8")
    ENV_PATH.chmod(0o600)
    user = pwd.getpwnam("getsync")
    os.chown(ENV_PATH, user.pw_uid, user.pw_gid)
    os.chown(backup, user.pw_uid, user.pw_gid)

    print(f"backup: {backup}")
    print(f"wrote: {ENV_PATH}")
    if removed:
        print("removed:", ", ".join(removed))


if __name__ == "__main__":
    main()
