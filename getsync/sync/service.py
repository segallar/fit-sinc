"""Sync delivery orchestrator (bootstrap: hammerhead → garmin)."""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from getsync.catalog.api import get_catalog
from getsync.contracts.activities import ActivitySink, ActivitySourceWithArtifacts
from getsync.contracts.persistence import ActivityCatalog
from getsync.garmin.upload_errors import (
    garmin_duplicate_log_message,
    garmin_duplicate_result,
    is_garmin_duplicate_upload,
)
from getsync.providers.bootstrap import register_default_providers
from getsync.providers.registry import get_sink, get_source
from getsync.state.store import Store
from getsync.storage.activity import ActivityStorage
from getsync.sync.infra.store_event_log import StoreSyncEventLog
from getsync.users.context import UserContext, as_context, resolve_user_context

logger = logging.getLogger("getsync.sync")

RETRY_DELAYS_SEC = (5, 15, 30)
BOOTSTRAP_SOURCE = "hammerhead"
BOOTSTRAP_SINK = "garmin"


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


def _catalog(ctx: UserContext) -> ActivityCatalog:
    return get_catalog(ctx)


def _events(ctx: UserContext) -> StoreSyncEventLog:
    return StoreSyncEventLog(_store(ctx))


def _ensure_providers() -> None:
    register_default_providers()


def _hammerhead_source(ctx: UserContext) -> ActivitySourceWithArtifacts:
    _ensure_providers()
    source = get_source(BOOTSTRAP_SOURCE)
    if not isinstance(source, ActivitySourceWithArtifacts):
        raise RuntimeError(f"{BOOTSTRAP_SOURCE!r} source does not support FIT artifacts")
    return source


def _garmin_sink(ctx: UserContext) -> ActivitySink:
    _ensure_providers()
    return get_sink(BOOTSTRAP_SINK)


def _meta_from_normalized(meta: Any) -> dict[str, Any]:
    if meta is None:
        return {}
    return {
        "name": meta.name,
        "activity_date": meta.activity_date,
        "distance": meta.distance,
        "duration": meta.duration,
    }


async def sync_activity(
    activity_id: str,
    *,
    force: bool = False,
    ctx: UserContext | None = None,
    user_id: str | None = None,
) -> SyncResult:
    user_ctx = as_context(ctx, user_id)
    catalog = _catalog(user_ctx)
    events = _events(user_ctx)
    hh = _hammerhead_source(user_ctx)
    sink = _garmin_sink(user_ctx)

    if not force and catalog.is_synced(user_ctx.user_id, activity_id):
        events.append(
            "skipped",
            "already synced",
            activity_id,
            user_id=user_ctx.user_id,
        )
        return SyncResult(activity_id, "skipped", "already synced")

    events.append("sync_started", "", activity_id, user_id=user_ctx.user_id)
    catalog.upsert_activity(user_ctx.user_id, activity_id, sync_status="pending")
    await _notify_activity_ui(user_ctx, activity_id, "pending")

    meta: dict[str, Any] = {}
    try:
        normalized = await hh.fetch_metadata(user_ctx, activity_id)
        meta = _meta_from_normalized(normalized)
        catalog.upsert_activity(
            user_ctx.user_id, activity_id, **meta, sync_status="pending"
        )
    except Exception as exc:
        logger.warning("activity metadata fetch failed %s: %s", activity_id, exc)

    fit_bytes: bytes | None = None
    last_error: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS_SEC, start=1):
        try:
            fit_bytes = await hh.download_fit(user_ctx, activity_id)
            break
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code in (404, 409, 425) and attempt < len(RETRY_DELAYS_SEC):
                events.append(
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
                events.append(
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
        catalog.mark_error(user_ctx.user_id, activity_id, msg)
        events.append("error", msg, activity_id, user_id=user_ctx.user_id)
        await _notify_activity_ui(user_ctx, activity_id, "error")
        return SyncResult(activity_id, "error", msg)

    artifacts = ActivityStorage(user_ctx)
    storage_key = artifacts.put_fit("hammerhead", activity_id, fit_bytes)
    fit_path = artifacts.open_fit_path(storage_key)
    events.append(
        "fit_saved",
        storage_key,
        activity_id,
        user_id=user_ctx.user_id,
    )

    filename = fit_path.name if fit_path else f"{activity_id}.fit"
    try:
        upload_result = await sink.upload_fit(user_ctx, activity_id, fit_bytes, filename)
        garmin_result = upload_result.raw or {"status": upload_result.status}
    except Exception as exc:
        if is_garmin_duplicate_upload(exc):
            garmin_result = garmin_duplicate_result()
            catalog.mark_synced(
                user_ctx.user_id,
                activity_id,
                garmin_result,
                storage_key=storage_key,
                **meta,
            )
            dup_msg = garmin_duplicate_log_message()
            events.append(
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
        catalog.upsert_activity(
            user_ctx.user_id,
            activity_id,
            sync_status="error",
            storage_key=storage_key,
            error_message=msg,
            **meta,
        )
        events.append("error", msg, activity_id, user_id=user_ctx.user_id)
        await _notify_activity_ui(user_ctx, activity_id, "error")
        return SyncResult(activity_id, "error", msg)

    catalog.mark_synced(
        user_ctx.user_id,
        activity_id,
        garmin_result,
        storage_key=storage_key,
        **meta,
    )
    events.append(
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
    source = _hammerhead_source(user_ctx)
    results: list[SyncResult] = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        page_result = await source.fetch_page(
            user_ctx, page=page, per_page=100, date_from=since
        )
        for item in page_result.items:
            result = await sync_activity(item.activity_id, ctx=user_ctx)
            results.append(result)
            logger.info("%s: %s — %s", result.activity_id, result.status, result.message)
        total_pages = max(1, page_result.total_pages)
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
