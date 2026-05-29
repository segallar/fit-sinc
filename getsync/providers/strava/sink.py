"""Strava activity sink adapter (FIT upload)."""

from __future__ import annotations

from getsync.contracts.activities import UploadResult
from getsync.contracts.connections import ConnectionStatus
from getsync.providers.strava.client import StravaClient, StravaNotConnectedError
from getsync.providers.strava.source import StravaSource
from getsync.users.context import UserContext


class StravaNotConfiguredError(RuntimeError):
    pass


class StravaSink:
    """Activity sink — FIT upload via Strava API (**3.9.3c**)."""

    sink_id = "strava"

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        status = StravaSource().connection_status(ctx)
        return ConnectionStatus(
            connected=status.connected,
            label="Strava",
            status_text=status.status_text,
            status_variant=status.status_variant,
            upload_ready=status.connected,
            details=status.details,
        )

    async def upload_fit(
        self,
        ctx: UserContext,
        activity_id: str,
        fit: bytes,
        filename: str,
    ) -> UploadResult:
        if not StravaClient(ctx).load_tokens():
            raise StravaNotConfiguredError(
                "Strava upload requires a connected account — connect Strava in Settings"
            )
        external_id = f"getsync:{ctx.user_id}:{activity_id}"
        try:
            raw = await StravaClient(ctx).upload_fit(
                fit,
                filename,
                external_id=external_id,
                name=filename.rsplit(".", 1)[0] if filename else None,
            )
        except StravaNotConnectedError as exc:
            raise StravaNotConfiguredError(str(exc)) from exc
        activity_id_out = raw.get("activity_id") if isinstance(raw, dict) else None
        if activity_id_out:
            return UploadResult(
                status="synced",
                message=f"strava activity {activity_id_out}",
                raw=raw if isinstance(raw, dict) else None,
            )
        error = raw.get("error") if isinstance(raw, dict) else None
        if isinstance(raw, dict):
            status_msg = str(raw.get("status") or error or "error")
        else:
            status_msg = "error"
        return UploadResult(
            status="error",
            message=status_msg,
            raw=raw if isinstance(raw, dict) else None,
        )
