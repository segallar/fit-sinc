"""Version, git commit, and deploy metadata for UI footer and /health."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from getsync import __version__

_BUILD_META_FILE = Path(__file__).resolve().parent / "_build_meta.json"
_COMMIT_FILE = Path(__file__).resolve().parent / "_git_commit.txt"
_REPO_ROOT = Path(__file__).resolve().parents[1]


def clear_build_info_cache() -> None:
    _build_meta.cache_clear()
    git_commit_short.cache_clear()


@lru_cache(maxsize=1)
def _build_meta() -> dict[str, Any]:
    if _BUILD_META_FILE.is_file():
        try:
            data = json.loads(_BUILD_META_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
    return {}


@lru_cache(maxsize=1)
def git_commit_short() -> str:
    """Short commit hash: meta file, env, legacy file, local git, or 'dev'."""
    meta = _build_meta()
    commit = meta.get("commit")
    if commit:
        return str(commit)[:12]
    env = os.environ.get("GETSYNC_GIT_COMMIT", "").strip()
    if env:
        return env[:12]
    if _COMMIT_FILE.is_file():
        text = _COMMIT_FILE.read_text(encoding="utf-8").strip()
        if text:
            return text[:12]
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        commit = proc.stdout.strip()
        if commit:
            return commit
    except (OSError, subprocess.SubprocessError):
        pass
    return "dev"


def deploy_number() -> int | None:
    meta = _build_meta()
    raw = meta.get("deploy_number")
    if raw is None:
        raw = os.environ.get("GETSYNC_DEPLOY_NUMBER", "").strip()
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def deployed_at_iso() -> str | None:
    meta = _build_meta()
    raw = meta.get("deployed_at")
    if not raw:
        raw = os.environ.get("GETSYNC_DEPLOYED_AT", "").strip()
    return str(raw).strip() or None


def deploy_time_footer() -> str | None:
    """Human-readable deploy time for footer (UTC)."""
    iso = deployed_at_iso()
    if not iso:
        return None
    try:
        normalized = iso.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
    except ValueError:
        return iso
    return dt.strftime("%d.%m.%Y %H:%M UTC")


def build_footer_text() -> str:
    parts = [f"GetSync v{__version__}"]
    commit = git_commit_short()
    if commit != "dev":
        parts.append(commit)
    number = deploy_number()
    if number is not None:
        parts.append(f"deploy #{number}")
    when = deploy_time_footer()
    if when:
        parts.append(when)
    return " · ".join(parts)
