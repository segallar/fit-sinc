"""Signed OAuth state for web flows (Hammerhead connect in settings)."""

from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SALT = "fit-sinc-hammerhead-oauth"
MAX_AGE_SEC = 600


def sign_hammerhead_oauth_state(user_id: str, secret: str) -> str:
    return URLSafeTimedSerializer(secret, salt=SALT).dumps({"user_id": user_id})


def verify_hammerhead_oauth_state(state: str, secret: str) -> str | None:
    if not state:
        return None
    try:
        payload = URLSafeTimedSerializer(secret, salt=SALT).loads(
            state, max_age=MAX_AGE_SEC
        )
    except (BadSignature, SignatureExpired):
        return None
    uid = payload.get("user_id") if isinstance(payload, dict) else None
    return str(uid) if uid else None
