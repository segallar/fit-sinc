import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from getsync import __version__
from getsync.build_info import deploy_number, deployed_at_iso, git_commit_short
from getsync.audit import record_startup
from getsync.config import get_settings
from getsync.logging_setup import configure_logging

configure_logging()
from getsync.garmin.web_refresh import refresh_web_session
from getsync.hammerhead.oauth import verify_webhook_signature
from getsync.state.store import Store
from getsync.sync.service import resolve_user_for_webhook, sync_activity
from getsync.users.context import UserContext
from getsync.users.bootstrap import apply_bootstrap_admin, registration_is_open
from getsync.users.migrate import infer_hammerhead_user_id
from getsync.web.admin_routes import router as admin_router
from getsync.web.app_routes import router as app_router
from getsync.web.auth import (
    install_auth_middleware,
    install_sessions,
    warn_insecure_session_config,
)
from getsync.web.settings_routes import router as settings_router
from getsync.web.register_routes import router as register_router
from getsync.web.site_routes import router as site_router
logger = logging.getLogger("getsync")


def _bootstrap() -> None:
    settings = get_settings()
    store = Store(settings.db_path)
    hh_uid = infer_hammerhead_user_id(settings)
    store.ensure_default_user(hammerhead_user_id=hh_uid)
    apply_bootstrap_admin(store, settings)
    record_startup(store, settings.data_dir)
    logger.info("bootstrap: default user ready (hh_user_id=%s)", hh_uid)
    for msg in warn_insecure_session_config():
        logger.warning("session config: %s", msg)


async def _jwt_refresh_loop() -> None:
    settings = get_settings()
    interval = max(60, settings.garmin_jwt_refresh_interval_sec)
    while True:
        store = Store(settings.db_path)
        for user in store.list_users():
            if user.disabled:
                continue
            ctx = UserContext(user.id, settings)
            if not ctx.garmin_web_dir.is_dir():
                continue
            try:
                result = await asyncio.to_thread(
                    refresh_web_session, ctx, trigger="background"
                )
                if result.get("refreshed"):
                    logger.info(
                        "background JWT refresh user=%s via %s",
                        user.id,
                        result.get("method"),
                    )
            except Exception as exc:
                logger.exception("background JWT refresh failed user=%s", user.id)
                try:
                    store.log_session_refresh(
                        "background",
                        "error",
                        str(exc)[:500],
                        user_id=user.id,
                    )
                except Exception:
                    pass
        await asyncio.sleep(interval)


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    _bootstrap()
    task = asyncio.create_task(_jwt_refresh_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="GetSync", version=__version__, lifespan=_lifespan)
# Auth middleware должен быть зарегистрирован раньше SessionMiddleware,
# иначе request.session недоступен (500 на /, /app, /admin).
install_auth_middleware(app)
install_sessions(app)
app.include_router(site_router)
app.include_router(register_router)
app.include_router(settings_router)
app.include_router(app_router)
app.include_router(admin_router)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _store() -> Store:
    return Store(get_settings().db_path)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.ico", media_type="image/x-icon")


@app.get("/health")
async def health() -> dict[str, str | bool | int | None]:
    return {
        "status": "ok",
        "service": "getsync",
        "version": __version__,
        "commit": git_commit_short(),
        "deploy_number": deploy_number(),
        "deployed_at": deployed_at_iso(),
        "registration_open": registration_is_open(),
    }


@app.post("/webhooks/hammerhead")
async def hammerhead_webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    body = await request.body()
    signature = request.headers.get("X-Hmac-Signature", "")
    settings = get_settings()

    if settings.hammerhead_webhook_secret:
        if not verify_webhook_signature(body, settings.hammerhead_webhook_secret, signature):
            logger.warning("webhook rejected: invalid HMAC signature")
            return JSONResponse({"status": "forbidden"}, status_code=403)
    elif signature:
        logger.warning("webhook HMAC present but HAMMERHEAD_WEBHOOK_SECRET not configured")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.warning("webhook invalid JSON")
        return JSONResponse({"status": "bad_request"}, status_code=400)

    activity_id = payload.get("activityId")
    hh_user_id = payload.get("userId")
    user_ctx = resolve_user_for_webhook(str(hh_user_id) if hh_user_id else None)
    logger.info(
        "webhook activityId=%s hammerheadUserId=%s tenant=%s",
        activity_id,
        hh_user_id,
        user_ctx.user_id,
    )

    if activity_id:
        store = _store()
        store.log_event(
            "webhook_received",
            f"hammerheadUserId={hh_user_id}",
            activity_id,
            user_id=user_ctx.user_id,
        )
        background_tasks.add_task(_run_sync, activity_id, user_ctx.user_id)
    else:
        logger.warning("webhook missing activityId: %s", body[:200])

    return JSONResponse({"status": "accepted"})


async def _run_sync(activity_id: str, user_id: str) -> None:
    try:
        result = await sync_activity(activity_id, user_id=user_id)
        logger.info(
            "webhook sync %s user=%s -> %s",
            activity_id,
            user_id,
            result.status,
        )
    except Exception:
        logger.exception("webhook sync failed for %s user=%s", activity_id, user_id)
