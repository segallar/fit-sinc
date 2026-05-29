"""Contract tests for built-in provider adapters."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from getsync.contracts.activities import (
    ActivitySink,
    ActivitySource,
    ActivitySourceWithArtifacts,
)
from getsync.providers.bootstrap import register_default_providers
from getsync.providers.garmin.sink import GarminSink
from getsync.providers.garmin.source import GarminSource
from getsync.providers.hammerhead.source import HammerheadSource
from getsync.providers.registry import get_sink, get_source, list_sources
from getsync.providers.strava.client import StravaClient
from getsync.providers.strava.sink import StravaSink
from getsync.providers.strava.source import StravaSource


def test_builtin_adapters_implement_protocols():
    hh = HammerheadSource()
    gm_src = GarminSource()
    gm_sink = GarminSink()
    st_src = StravaSource()
    st_sink = StravaSink()
    assert isinstance(hh, ActivitySource)
    assert isinstance(hh, ActivitySourceWithArtifacts)
    assert isinstance(gm_src, ActivitySource)
    assert isinstance(gm_sink, ActivitySink)
    assert isinstance(st_src, ActivitySource)
    assert isinstance(st_sink, ActivitySink)


def test_bootstrap_registers_default_providers():
    register_default_providers()
    ids = {s.source_id for s in list_sources()}
    assert ids >= {"hammerhead", "garmin", "strava"}
    assert get_source("hammerhead").source_id == "hammerhead"
    assert get_sink("garmin").sink_id == "garmin"


def test_default_refresh_sources_includes_strava_when_tokens_exist():
    from getsync.catalog.application.refresh import default_refresh_sources

    ctx = Mock()
    with patch("getsync.catalog.application.refresh.StravaClient") as mock_cls:
        mock_cls.return_value.load_tokens.return_value = None
        assert default_refresh_sources(ctx) == ("hammerhead", "garmin")
        mock_cls.return_value.load_tokens.return_value = object()
        assert default_refresh_sources(ctx) == ("hammerhead", "garmin", "strava")


@pytest.mark.asyncio
async def test_strava_source_returns_empty_page_without_tokens():
    register_default_providers()
    src = get_source("strava")
    with patch.object(StravaClient, "load_tokens", return_value=None):
        page = await src.fetch_page(Mock(user_id="u1"), page=1)
    assert page.items == ()
