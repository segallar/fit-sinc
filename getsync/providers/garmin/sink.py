"""Garmin Connect activity sink adapter (FIT upload)."""

from __future__ import annotations

import asyncio
from typing import Any

from getsync.contracts.activities import UploadResult
from getsync.contracts.connections import ConnectionStatus
from getsync.garmin.session import garmin_status, upload_fit as garmin_upload_fit
from getsync.users.context import UserContext


class GarminSink:
    """ActivitySink for Garmin Connect FIT upload."""

    sink_id = "garmin"

    def connection_status(self, ctx: UserContext) -> ConnectionStatus:
        raw = garmin_status(ctx)
        web = raw.get("web") or {}
        upload_ready = bool(raw.get("upload_ready"))
        connected = bool(raw.get("connected"))
        if upload_ready:
            text = "upload ready"
            variant = "success"
        elif connected:
            text = "connected, upload not ready"
            variant = "warning"
        else:
            text = str(web.get("reason") or "not connected")
            variant = "secondary"
        return ConnectionStatus(
            connected=connected,
            label="Garmin Connect",
            status_text=text,
            status_variant=variant,
            upload_ready=upload_ready,
        )

    async def upload_fit(
        self,
        ctx: UserContext,
        activity_id: str,
        fit: bytes,
        filename: str,
    ) -> UploadResult:
        def _run() -> dict[str, Any]:
            result = garmin_upload_fit(fit, filename, ctx)
            if isinstance(result, dict):
                return result
            return {"status": "ok", "result": result}

        raw = await asyncio.to_thread(_run)
        status = str(raw.get("status") or "synced")
        return UploadResult(status=status, raw=raw)
