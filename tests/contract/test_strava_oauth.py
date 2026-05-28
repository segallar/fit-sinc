"""Strava OAuth contract tests (Phase 0 spike)."""

from getsync.providers.strava.oauth import TokenSet


def test_token_set_from_response_with_expires_at():
    payload = {
        "access_token": "at",
        "refresh_token": "rt",
        "expires_at": 1_700_000_000,
        "athlete": {"id": 42},
    }
    tokens = TokenSet.from_response(payload)
    assert tokens.access_token == "at"
    assert tokens.refresh_token == "rt"
    assert tokens.expires_at == 1_700_000_000
    assert tokens.athlete_id == 42


def test_token_set_roundtrip_dict():
    tokens = TokenSet(
        access_token="a",
        refresh_token="r",
        expires_at=1_700_000_000,
        athlete_id=7,
        obtained_at=1_699_999_000,
    )
    restored = TokenSet.from_dict(tokens.to_dict())
    assert restored == tokens
