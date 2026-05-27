"""Application logging: stderr (journald) + optional rotating file under data/logs/."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_done = False


def reset_logging_for_tests() -> None:
    """Clear handlers so tests can re-configure logging."""
    global _done
    _done = False
    log = logging.getLogger("getsync")
    for handler in log.handlers[:]:
        handler.close()
        log.removeHandler(handler)


def configure_logging(*, force: bool = False) -> Path | None:
    """Attach stderr + rotating file handlers to the ``getsync`` logger tree."""
    global _done
    if _done and not force:
        from getsync.config import get_settings

        return get_settings().resolved_log_file

    from getsync.config import get_settings

    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    log = logging.getLogger("getsync")
    log.setLevel(level)
    log.propagate = False
    if force:
        for handler in log.handlers[:]:
            handler.close()
            log.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    if not any(isinstance(h, logging.StreamHandler) for h in log.handlers):
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(formatter)
        log.addHandler(stream)

    log_file = settings.resolved_log_file
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        if not any(
            isinstance(h, RotatingFileHandler)
            and getattr(h, "baseFilename", "") == str(log_file)
            for h in log.handlers
        ):
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=settings.log_max_bytes,
                backupCount=settings.log_backup_count,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            log.addHandler(file_handler)
        log.info("logging to %s", log_file)

    _done = True
    return log_file
