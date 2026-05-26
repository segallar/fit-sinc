"""Version and git commit for UI footer and /health."""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

from getsync import __version__

_COMMIT_FILE = Path(__file__).resolve().parent / "_git_commit.txt"
_REPO_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def git_commit_short() -> str:
    """Short commit hash: env, deploy file, local git, or 'dev'."""
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


def build_footer_text() -> str:
    commit = git_commit_short()
    if commit == "dev":
        return f"GetSync v{__version__}"
    return f"GetSync v{__version__} · {commit}"
