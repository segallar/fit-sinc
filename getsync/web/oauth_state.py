"""Signed OAuth state for web flows (provider connect in settings)."""

from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SALT_HAMMERHEAD = "getsync-hammerhead-oauth"
SALT_STRAVA = "getsync-strava-oauth"
MAX_AGE_SEC = 600


def _sign_oauth_state(user_id: str, secret: str, salt: str) -> str:
    return URLSafeTimedSerializer(secret, salt=salt).dumps({"user_id": user_id})


def _verify_oauth_state(state: str, secret: str, salt: str) -> str | None:
    if not state:
        return None
    try:
        payload = URLSafeTimedSerializer(secret, salt=salt).loads(
            state, max_age=MAX_AGE_SEC
        )
    except (BadSignature, SignatureExpired):
        return None
    uid = payload.get("user_id") if isinstance(payload, dict) else None
    return str(uid) if uid else None


def sign_hammerhead_oauth_state(user_id: str, secret: str) -> str:
    return _sign_oauth_state(user_id, secret, SALT_HAMMERHEAD)


def verify_hammerhead_oauth_state(state: str, secret: str) -> str | None:
    return _verify_oauth_state(state, secret, SALT_HAMMERHEAD)


def sign_strava_oauth_state(user_id: str, secret: str) -> str:
    return _sign_oauth_state(user_id, secret, SALT_STRAVA)


def verify_strava_oauth_state(state: str, secret: str) -> str | None:
    return _verify_oauth_state(state, secret, SALT_STRAVA)
