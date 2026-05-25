import asyncio
import io
import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from fit_sinc.config import Settings, get_settings
from fit_sinc.garmin.session import upload_fit
from fit_sinc.hammerhead.client import HammerheadClient
from fit_sinc.state.store import Store

logger = logging.getLogger("fit_sinc.sync")

RETRY_DELAYS_SEC = (5, 15, 30)


@dataclass(frozen=True)
class SyncResult:
    activity_id: str
    status: str  # synced, skipped, error
    message: str = ""


def _fit_path(settings: Settings, activity_id: str) -> Path:
    settings.fits_dir.mkdir(parents=True, exist_ok=True)
    safe = activity_id.replace("/", "_")
    return settings.fits_dir / f"{safe}.fit"


def _store(settings: Settings | None = None) -> Store:
    settings = settings or get_settings()
    return Store(settings.db_path)


def _meta_from_hh(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": data.get("name"),
        "activity_date": data.get("createdAt"),
        "distance": data.get("distance"),
        "duration": data.get("duration"),
    }


async def sync_activity(
    activity_id: str,
    *,
    force: bool = False,
    settings: Settings | None = None,
) -> SyncResult:
    settings = settings or get_settings()
    store = _store(settings)
    hh = HammerheadClient(settings)

    if not force and store.is_synced(activity_id):
        store.log_event("skipped", "already synced", activity_id)
        return SyncResult(activity_id, "skipped", "already synced")

    store.log_event("sync_started", "", activity_id)
    store.upsert_activity(activity_id, sync_status="pending")

    meta: dict[str, Any] = {}
    try:
        meta = _meta_from_hh(await hh.get_activity(activity_id))
        store.upsert_activity(activity_id, **meta, sync_status="pending")
    except Exception as exc:
        logger.warning("activity metadata fetch failed %s: %s", activity_id, exc)

    fit_bytes: bytes | None = None
    last_error: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS_SEC, start=1):
        try:
            fit_bytes = await hh.download_fit(activity_id)
            break
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code in (404, 409, 425) and attempt < len(RETRY_DELAYS_SEC):
                store.log_event(
                    "fit_retry",
                    f"attempt {attempt}, wait {delay}s: HTTP {exc.response.status_code}",
                    activity_id,
                )
                await asyncio.sleep(delay)
                continue
            raise
        except Exception as exc:
            last_error = exc
            if attempt < len(RETRY_DELAYS_SEC):
                store.log_event("fit_retry", f"attempt {attempt}: {exc}", activity_id)
                await asyncio.sleep(delay)
                continue
            raise

    if fit_bytes is None:
        msg = str(last_error or "FIT download failed")
        store.mark_error(activity_id, msg)
        store.log_event("error", msg, activity_id)
        return SyncResult(activity_id, "error", msg)

    fit_path = _fit_path(settings, activity_id)
    fit_path.write_bytes(fit_bytes)
    store.log_event("fit_saved", str(fit_path), activity_id)

    try:
        garmin_result = upload_fit(
            fit_bytes,
            fit_path.name,
            settings=settings,
        )
    except Exception as exc:
        msg = f"Garmin upload failed: {exc}"
        store.upsert_activity(
            activity_id,
            sync_status="error",
            fit_path=str(fit_path),
            error_message=msg,
            **meta,
        )
        store.log_event("error", msg, activity_id)
        return SyncResult(activity_id, "error", msg)

    store.mark_synced(
        activity_id,
        str(fit_path),
        garmin_result,
        **meta,
    )
    store.log_event(
        "garmin_uploaded",
        json.dumps(garmin_result, default=str)[:500],
        activity_id,
    )
    logger.info("synced %s -> Garmin (%d bytes)", activity_id, len(fit_bytes))
    return SyncResult(activity_id, "synced", str(fit_path))


async def backfill_since(
    since: date,
    *,
    settings: Settings | None = None,
) -> list[SyncResult]:
    settings = settings or get_settings()
    hh = HammerheadClient(settings)
    results: list[SyncResult] = []
    page = 1

    while True:
        payload = await hh.list_activities(
            page=page,
            per_page=100,
            start_date=since.isoformat(),
        )
        items = payload.get("data") or []
        for item in items:
            aid = item["id"]
            result = await sync_activity(aid, settings=settings)
            results.append(result)
            logger.info("%s: %s — %s", result.activity_id, result.status, result.message)

        total_pages = payload.get("totalPages") or 1
        if page >= total_pages:
            break
        page += 1

    return results
