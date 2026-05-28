"""Strava activity sink adapter (planned — upload not wired yet)."""

from __future__ import annotations

from getsync.contracts.activities import UploadResult
from getsync.contracts.connections import ConnectionStatus
from getsync.users.context import UserContext


class StravaNotConfiguredError(RuntimeError):
    pass


class StravaSink:
    """ActivitySink placeholder until Strava OAuth + uploads API."""

    sink_id = "strava"

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        return ConnectionStatus(
            connected=False,
            label="Strava",
            status_text="planned",
            status_variant="secondary",
            upload_ready=False,
        )

    async def upload_fit(
        self,
        ctx: UserContext,
        activity_id: str,
        fit: bytes,
        filename: str,
    ) -> UploadResult:
        raise StravaNotConfiguredError(
            "Strava upload is not configured yet — connect Strava in Settings (planned)"
        )
