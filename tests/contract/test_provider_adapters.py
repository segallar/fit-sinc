"""Contract tests for built-in provider adapters."""

from __future__ import annotations

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


@pytest.mark.asyncio
async def test_strava_source_returns_empty_page():
    from unittest.mock import Mock

    register_default_providers()
    src = get_source("strava")
    page = await src.fetch_page(Mock(), page=1)
    assert page.items == ()
