"""Strava activity sink adapter (planned — upload not wired yet)."""

from __future__ import annotations

from getsync.contracts.activities import UploadResult
from getsync.contracts.connections import ConnectionStatus
from getsync.users.context import UserContext


class StravaNotConfiguredError(RuntimeError):
    pass


class StravaSink:
    """Activity sink — upload in **3.9.3c** Phase 4."""

    sink_id = "strava"

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        from getsync.providers.strava.source import StravaSource

        status = StravaSource().connection_status(ctx)
        return ConnectionStatus(
            connected=status.connected,
            label="Strava",
            status_text=status.status_text,
            status_variant=status.status_variant,
            upload_ready=False,
            details=status.details,
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
