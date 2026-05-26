"""Read legacy fit_sinc_session cookies during GetSync rename (R7)."""

from __future__ import annotations

import json
from base64 import b64decode

import itsdangerous
from itsdangerous.exc import BadSignature
from starlette.requests import Request

LEGACY_SESSION_COOKIE = "fit_sinc_session"
SESSION_COOKIE = "getsync_session"


def legacy_session_payload(
    request: Request,
    *,
    secret_key: str,
    max_age: int | None = 14 * 24 * 3600,
) -> dict | None:
    """Decode Starlette session from the pre-rename cookie name."""
    if request.cookies.get(SESSION_COOKIE):
        return None
    raw = request.cookies.get(LEGACY_SESSION_COOKIE)
    if not raw:
        return None
    signer = itsdangerous.TimestampSigner(secret_key)
    try:
        data = signer.unsign(raw.encode("utf-8"), max_age=max_age)
        payload = json.loads(b64decode(data))
        return payload if isinstance(payload, dict) else None
    except BadSignature:
        return None
