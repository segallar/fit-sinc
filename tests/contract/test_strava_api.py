"""Strava provider contract tests (**3.9.3c**)."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from getsync.providers.strava.client import StravaClient
from getsync.providers.strava.normalize import item_to_normalized
from getsync.providers.strava.oauth import TokenSet
from getsync.providers.strava.sink import StravaSink
from getsync.providers.strava.source import StravaSource
from getsync.users.context import UserContext


def test_item_to_normalized_maps_strava_fields():
    row = item_to_normalized(
        {
            "id": 12345,
            "name": "Morning Ride",
            "start_date_local": "2026-05-28T07:30:00Z",
            "distance": 32100.5,
            "moving_time": 3600,
            "sport_type": "Ride",
        },
        "user-1",
    )
    assert row is not None
    assert row.source == "strava"
    assert row.activity_id == "12345"
    assert row.name == "Morning Ride"
    assert row.distance == 32100.5
    assert row.duration == 3600.0
    assert row.activity_type == "Ride"


@pytest.mark.asyncio
async def test_strava_source_fetch_page_maps_api_response():
    src = StravaSource()
    ctx = Mock(user_id="u1")
    tokens = TokenSet(
        access_token="at",
        refresh_token="rt",
        expires_at=9_999_999_999.0,
        athlete_id=1,
        obtained_at=1.0,
    )
    with patch.object(StravaClient, "load_tokens", return_value=tokens):
        with patch.object(
            StravaClient,
            "list_activities",
            new_callable=AsyncMock,
            return_value=[
                {
                    "id": 99,
                    "name": "Test",
                    "start_date": "2026-05-01T10:00:00Z",
                    "distance": 1000,
                    "moving_time": 600,
                    "type": "Ride",
                }
            ],
        ):
            page = await src.fetch_page(ctx, page=1, per_page=50)
    assert len(page.items) == 1
    assert page.items[0].activity_id == "99"
    assert page.total_pages == 1


@pytest.mark.asyncio
async def test_strava_sink_upload_success():
    sink = StravaSink()
    ctx = Mock(user_id="u1")
    tokens = TokenSet(
        access_token="at",
        refresh_token="rt",
        expires_at=9_999_999_999.0,
        athlete_id=1,
        obtained_at=1.0,
    )
    with patch.object(StravaClient, "load_tokens", return_value=tokens):
        with patch.object(
            StravaClient,
            "upload_fit",
            new_callable=AsyncMock,
            return_value={"activity_id": 555, "status": "ready"},
        ):
            result = await sink.upload_fit(ctx, "hh-1", b"FIT", "ride.fit")
    assert result.status == "synced"
    assert "555" in result.message


@pytest.mark.asyncio
async def test_strava_client_refresh_on_expired_token():
    with tempfile.TemporaryDirectory() as tmp:
        from getsync.config import get_settings

        data_dir = Path(tmp) / "data"
        data_dir.mkdir()
        import os

        os.environ["DATA_DIR"] = str(data_dir)
        os.environ["STRAVA_CLIENT_ID"] = "1"
        os.environ["STRAVA_CLIENT_SECRET"] = "secret"
        get_settings.cache_clear()
        settings = get_settings()
        ctx = UserContext("default", settings)
        client = StravaClient(ctx)
        expired = TokenSet(
            access_token="old",
            refresh_token="rt",
            expires_at=1.0,
            athlete_id=7,
            obtained_at=0.0,
        )
        client.save_tokens(expired)
        refreshed = TokenSet(
            access_token="new",
            refresh_token="rt2",
            expires_at=9_999_999_999.0,
            athlete_id=7,
            obtained_at=100.0,
        )
        with patch.object(
            StravaClient,
            "_oauth",
        ) as mock_oauth_factory:
            mock_oauth = Mock()
            mock_oauth.refresh = AsyncMock(return_value=refreshed)
            mock_oauth_factory.return_value = mock_oauth
            tokens = await client.ensure_tokens()
        assert tokens.access_token == "new"
        assert client.load_tokens() is not None
        assert client.load_tokens().access_token == "new"
        get_settings.cache_clear()
