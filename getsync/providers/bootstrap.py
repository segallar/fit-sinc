"""Register default provider adapters at application startup."""

from __future__ import annotations

from getsync.providers.garmin.sink import GarminSink
from getsync.providers.garmin.source import GarminSource
from getsync.providers.hammerhead.source import HammerheadSource
from getsync.providers.registry import register_sink, register_source
from getsync.providers.strava.sink import StravaSink
from getsync.providers.strava.source import StravaSource

_registered = False


def register_default_providers() -> None:
    """Idempotent registration of built-in source/sink adapters."""
    global _registered
    if _registered:
        return
    register_source(HammerheadSource())
    register_source(GarminSource())
    register_source(StravaSource())
    register_sink(GarminSink())
    register_sink(StravaSink())
    _registered = True
