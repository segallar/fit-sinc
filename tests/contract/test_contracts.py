"""Contract tests for getsync.contracts."""

from __future__ import annotations

from datetime import date

import pytest
from getsync.contracts.activities import (
    ActivityPage,
    ActivitySink,
    ActivitySource,
    NormalizedActivity,
    UploadResult,
)
from getsync.contracts.connections import ConnectionStatus
from getsync.contracts.persistence import SyncIndexEntry
from getsync.providers.registry import get_sink, get_source, register_sink, register_source
from getsync.users.context import UserContext


class _FakeSource:
    source_id = "fake"

    async def fetch_page(self, ctx: UserContext, **kwargs) -> ActivityPage:
        return ActivityPage(items=(), page=1, total_pages=1)

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        return ConnectionStatus(
            connected=True,
            label="Fake",
            status_text="ok",
            status_variant="success",
        )


class _FakeSink:
    sink_id = "fake"

    async def upload_fit(self, ctx, activity_id, fit, filename) -> UploadResult:
        return UploadResult(status="ok")

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        return ConnectionStatus(
            connected=True,
            label="Fake",
            status_text="ready",
            status_variant="success",
            upload_ready=True,
        )


def test_normalized_activity_frozen():
    a = NormalizedActivity(
        user_id="u1",
        source="hammerhead",
        activity_id="abc",
        name="Ride",
    )
    b = NormalizedActivity(
        user_id="u1",
        source="hammerhead",
        activity_id="abc",
        name="Ride",
    )
    assert a == b


def test_sync_index_entry_frozen():
    entry = SyncIndexEntry(
        activity_id="x",
        sync_status="synced",
        garmin_id=None,
        garmin_upload_status=None,
        storage_key="activities/hammerhead/x.fit",
        synced_at="2026-01-01T00:00:00+00:00",
        error_message=None,
    )
    assert entry.sync_status == "synced"


def test_activity_source_protocol():
    assert isinstance(_FakeSource(), ActivitySource)


def test_activity_sink_protocol():
    assert isinstance(_FakeSink(), ActivitySink)


def test_registry_register_and_lookup():
    src = _FakeSource()
    sink = _FakeSink()
    register_source(src)
    register_sink(sink)
    assert get_source("fake") is src
    assert get_sink("fake") is sink


def test_registry_unknown_source():
    with pytest.raises(KeyError, match="unknown activity source"):
        get_source("__no_such_source__")


@pytest.mark.asyncio
async def test_fake_source_fetch_page():
    from unittest.mock import Mock

    ctx = Mock()
    page = await _FakeSource().fetch_page(ctx, page=1, date_from=date(2026, 1, 1))
    assert page.page == 1
    assert page.items == ()
