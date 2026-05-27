import asyncio
import io
import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import httpx

from getsync.garmin.session import upload_fit
from getsync.garmin.upload_errors import (
    garmin_duplicate_log_message,
    garmin_duplicate_result,
    is_garmin_duplicate_upload,
)
from getsync.hammerhead.client import HammerheadClient
from getsync.state.store import Store
from getsync.storage.activity import ActivityStorage
from getsync.users.context import UserContext, as_context, resolve_user_context

logger = logging.getLogger("getsync.sync")

RETRY_DELAYS_SEC = (5, 15, 30)


async def _notify_activity_ui(user_ctx: UserContext, activity_id: str, sync_status: str) -> None:
    try:
        from getsync.web.realtime import notify_activity_updated

        await notify_activity_updated(user_ctx.user_id, activity_id, sync_status)
    except Exception:
        logger.debug("realtime notify failed", exc_info=True)


@dataclass(frozen=True)
class SyncResult:
    activity_id: str
    status: str  # synced, skipped, error
    message: str = ""


def _store(ctx: UserContext) -> Store:
    return Store(ctx.db_path)


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
    ctx: UserContext | None = None,
    user_id: str | None = None,
) -> SyncResult:
    user_ctx = as_context(ctx, user_id)
    store = _store(user_ctx)
    hh = HammerheadClient(user_ctx)

    if not force and store.is_synced(user_ctx.user_id, activity_id):
        store.log_event(
            "skipped",
            "already synced",
            activity_id,
            user_id=user_ctx.user_id,
        )
        return SyncResult(activity_id, "skipped", "already synced")

    store.log_event("sync_started", "", activity_id, user_id=user_ctx.user_id)
    store.upsert_activity(user_ctx.user_id, activity_id, sync_status="pending")
    await _notify_activity_ui(user_ctx, activity_id, "pending")

    meta: dict[str, Any] = {}
    try:
        meta = _meta_from_hh(await hh.get_activity(activity_id))
        store.upsert_activity(
            user_ctx.user_id, activity_id, **meta, sync_status="pending"
        )
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
                    user_id=user_ctx.user_id,
                )
                await asyncio.sleep(delay)
                continue
            raise
        except Exception as exc:
            last_error = exc
            if attempt < len(RETRY_DELAYS_SEC):
                store.log_event(
                    "fit_retry",
                    f"attempt {attempt}: {exc}",
                    activity_id,
                    user_id=user_ctx.user_id,
                )
                await asyncio.sleep(delay)
                continue
            raise

    if fit_bytes is None:
        msg = str(last_error or "FIT download failed")
        store.mark_error(user_ctx.user_id, activity_id, msg)
        store.log_event("error", msg, activity_id, user_id=user_ctx.user_id)
        await _notify_activity_ui(user_ctx, activity_id, "error")
        return SyncResult(activity_id, "error", msg)

    artifacts = ActivityStorage(user_ctx)
    storage_key = artifacts.put_fit("hammerhead", activity_id, fit_bytes)
    fit_path = artifacts.open_fit_path(storage_key)
    store.log_event(
        "fit_saved",
        storage_key,
        activity_id,
        user_id=user_ctx.user_id,
    )

    try:
        garmin_result = upload_fit(
            fit_bytes,
            fit_path.name if fit_path else f"{activity_id}.fit",
            user_ctx,
        )
    except Exception as exc:
        if is_garmin_duplicate_upload(exc):
            garmin_result = garmin_duplicate_result()
            store.mark_synced(
                user_ctx.user_id,
                activity_id,
                garmin_result,
                storage_key=storage_key,
                **meta,
            )
            dup_msg = garmin_duplicate_log_message()
            store.log_event(
                "garmin_duplicate",
                dup_msg,
                activity_id,
                user_id=user_ctx.user_id,
            )
            logger.info(
                "synced %s -> Garmin duplicate (409) for user %s",
                activity_id,
                user_ctx.user_id,
            )
            await _notify_activity_ui(user_ctx, activity_id, "synced")
            return SyncResult(activity_id, "synced", dup_msg)
        msg = f"Garmin upload failed: {exc}"
        store.upsert_activity(
            user_ctx.user_id,
            activity_id,
            sync_status="error",
            storage_key=storage_key,
            error_message=msg,
            **meta,
        )
        store.log_event("error", msg, activity_id, user_id=user_ctx.user_id)
        await _notify_activity_ui(user_ctx, activity_id, "error")
        return SyncResult(activity_id, "error", msg)

    store.mark_synced(
        user_ctx.user_id,
        activity_id,
        garmin_result,
        storage_key=storage_key,
        **meta,
    )
    store.log_event(
        "garmin_uploaded",
        json.dumps(garmin_result, default=str)[:500],
        activity_id,
        user_id=user_ctx.user_id,
    )
    logger.info(
        "synced %s -> Garmin for user %s (%d bytes)",
        activity_id,
        user_ctx.user_id,
        len(fit_bytes),
    )
    await _notify_activity_ui(user_ctx, activity_id, "synced")
    return SyncResult(activity_id, "synced", storage_key)


async def backfill_since(
    since: date,
    *,
    ctx: UserContext | None = None,
    user_id: str | None = None,
) -> list[SyncResult]:
    user_ctx = as_context(ctx, user_id)
    hh = HammerheadClient(user_ctx)
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
            result = await sync_activity(aid, ctx=user_ctx)
            results.append(result)
            logger.info("%s: %s — %s", result.activity_id, result.status, result.message)

        total_pages = payload.get("totalPages") or 1
        if page >= total_pages:
            break
        page += 1

    return results


def resolve_user_for_webhook(hammerhead_user_id: str | None) -> UserContext:
    settings = resolve_user_context().settings
    store = Store(settings.db_path)
    if hammerhead_user_id:
        user = store.get_user_by_hammerhead_id(hammerhead_user_id)
        if user:
            return UserContext(user.id, settings)
    return resolve_user_context(settings.default_user_id)
