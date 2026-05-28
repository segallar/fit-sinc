"""Source/sink lookup by provider id."""

from __future__ import annotations

from getsync.contracts.activities import ActivitySink, ActivitySource

_SOURCES: dict[str, ActivitySource] = {}
_SINKS: dict[str, ActivitySink] = {}


def register_source(source: ActivitySource) -> None:
    _SOURCES[source.source_id] = source


def register_sink(sink: ActivitySink) -> None:
    _SINKS[sink.sink_id] = sink


def list_sources() -> tuple[ActivitySource, ...]:
    return tuple(_SOURCES.values())


def list_sinks() -> tuple[ActivitySink, ...]:
    return tuple(_SINKS.values())


def get_source(source_id: str) -> ActivitySource:
    try:
        return _SOURCES[source_id]
    except KeyError as exc:
        raise KeyError(f"unknown activity source: {source_id!r}") from exc


def get_sink(sink_id: str) -> ActivitySink:
    try:
        return _SINKS[sink_id]
    except KeyError as exc:
        raise KeyError(f"unknown activity sink: {sink_id!r}") from exc
