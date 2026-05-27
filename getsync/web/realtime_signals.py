"""Schedule WebSocket UI refreshes from sync code (must run inside asyncio loop)."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

logger = logging.getLogger("getsync.web.realtime_signals")

T = TypeVar("T")


def _schedule(coro_fn: Callable[[], Awaitable[T]]) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    task = loop.create_task(coro_fn())

    def _done(t: asyncio.Task[T]) -> None:
        try:
            t.result()
        except Exception:
            logger.debug("realtime notify failed", exc_info=True)

    task.add_done_callback(_done)


def schedule_admin_log_refresh() -> None:
    async def _run() -> None:
        from getsync.web.realtime import notify_admin_log_refresh

        await notify_admin_log_refresh()

    _schedule(_run)


def schedule_admin_health_refresh() -> None:
    async def _run() -> None:
        from getsync.web.realtime import notify_admin_health_refresh

        await notify_admin_health_refresh()

    _schedule(_run)
