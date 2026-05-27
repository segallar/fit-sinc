#!/usr/bin/env python3
"""Apply DOC-CONVENTION metadata line to docs (one-off / maintenance)."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

VERSION = "0.7.0"
ARCHIVE_VERSION = "0.6.0"
ROOT = Path(__file__).resolve().parents[1]

# created, updated — ISO dates; None updated → use git
FILES: dict[str, tuple[str, str | None, str | None]] = {
    "docs/README.md": ("2026-05-26", "2026-05-27", VERSION),
    "docs/DOC-CONVENTION.md": ("2026-05-26", "2026-05-26", VERSION),
    "docs/PLAN.md": ("2026-05-25", "2026-05-27", VERSION),
    "docs/ARCHITECTURE.md": ("2026-05-25", "2026-05-27", VERSION),
    "docs/CI-CD.md": ("2026-05-25", "2026-05-27", VERSION),
    "docs/TESTING.md": ("2026-05-26", "2026-05-27", VERSION),
    "docs/APP-UI.md": ("2026-05-26", "2026-05-27", VERSION),
    "docs/UI.md": ("2026-05-25", "2026-05-26", VERSION),
    "docs/STORAGE.md": ("2026-05-26", "2026-05-27", VERSION),
    "docs/DATABASE.md": ("2026-05-26", "2026-05-27", VERSION),
    "docs/CONNECTIONS.md": ("2026-05-26", "2026-05-26", VERSION),
    "docs/API_HAMMERHEAD.md": ("2026-05-25", "2026-05-26", VERSION),
    "docs/API_GARMIN.md": ("2026-05-25", "2026-05-26", VERSION),
    "docs/2.1-REGISTER.md": ("2026-05-26", "2026-05-26", VERSION),
    "docs/2.1e-EMAIL.md": ("2026-05-26", "2026-05-26", VERSION),
    "docs/3.4-OAUTH-LOGIN.md": ("2026-05-26", "2026-05-26", VERSION),
    "docs/3.11-GARMIN-PULL.md": ("2026-05-26", "2026-05-27", VERSION),
    "docs/archive/5b-DECISIONS.md": ("2026-05-25", "2026-05-26", ARCHIVE_VERSION),
    "docs/design/README.md": ("2026-05-26", "2026-05-27", VERSION),
    "docs/design/SCREENS.md": ("2026-05-26", "2026-05-27", VERSION),
    "docs/design/DESIGN-FEEDBACK.md": ("2026-05-26", "2026-05-26", VERSION),
    "docs/archive/README.md": ("2026-05-27", "2026-05-27", ARCHIVE_VERSION),
    "docs/archive/1.5-RENAME.md": ("2026-05-25", "2026-05-27", ARCHIVE_VERSION),
    "docs/archive/PLAN-ARCHIVE.md": ("2026-05-25", "2026-05-26", ARCHIVE_VERSION),
    "CHANGELOG.md": ("2026-05-26", "2026-05-26", VERSION),
}

META_RE = re.compile(
    r"^> \*\*Создано:\*\* .+ · \*\*Обновлено:\*\* .+ · \*\*Версия:\*\* .+$",
    re.MULTILINE,
)
OLD_UPDATED_RE = re.compile(r"^> \*\*Обновлено:\*\* \d{4}-\d{2}-\d{2}\s*$", re.MULTILINE)


def git_date(path: Path, created: bool) -> str:
    flag = "--diff-filter=A" if created else ""
    cmd = ["git", "log", flag, "-1", "--format=%ad", "--date=short", "--", str(path)]
    cmd = [c for c in cmd if c]
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
        return out or "2026-05-26"
    except subprocess.CalledProcessError:
        return "2026-05-26"


def meta_line(created: str, updated: str, version: str) -> str:
    return f"> **Создано:** {created} · **Обновлено:** {updated} · **Версия:** {version}  "


def archive_status_line() -> str:
    return "> **Статус:** архив — не обновлять под новые задачи; актуально [PLAN.md](../PLAN.md).  "


def apply(path: Path, created: str, updated: str | None, version: str) -> None:
    rel = path.relative_to(ROOT).as_posix()
    if updated is None:
        updated = git_date(path, created=False)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if not lines or not lines[0].startswith("# "):
        return

    ml = meta_line(created, updated, version) + "\n"
    is_archive = "docs/archive/" in rel and path.name != "README.md"
    status = archive_status_line() + "\n" if rel.startswith("docs/archive/") else ""

    # Remove old meta / standalone updated
    body = "".join(lines)
    body = META_RE.sub("", body)
    body = OLD_UPDATED_RE.sub("", body)
    lines = body.splitlines(keepends=True)

    i = 0
    while i < len(lines) and not lines[i].startswith("# "):
        i += 1
    if i >= len(lines):
        return

    insert_at = i + 1
    # Skip blank after H1
    while insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1

    # If next lines are blockquote, replace first if it looks like meta or old updated
    if insert_at < len(lines) and lines[insert_at].startswith(">"):
        # Collect contiguous blockquote lines
        bq_end = insert_at
        while bq_end < len(lines) and (
            lines[bq_end].startswith(">") or (lines[bq_end].strip() == "" and bq_end == insert_at + 1)
        ):
            if lines[bq_end].startswith(">"):
                bq_end += 1
            else:
                break
        # Drop leading meta/updated lines from block
        rest_start = insert_at
        while rest_start < bq_end:
            s = lines[rest_start].strip()
            if (
                s.startswith("> **Создано:**")
                or s.startswith("> **Обновлено:**")
                or (rel.startswith("docs/archive/") and s.startswith("> **Статус:** архив"))
            ):
                rest_start += 1
            else:
                break
        new_block = [ml]
        if status and rel.startswith("docs/archive/"):
            new_block.append(status)
        new_block.extend(lines[rest_start:bq_end])
        lines = lines[:insert_at] + new_block + lines[bq_end:]
    else:
        new_block = [ml]
        if status:
            new_block.append(status)
        if insert_at < len(lines) and lines[insert_at - 1].endswith("\n"):
            pass
        lines = lines[:insert_at] + new_block + lines[insert_at:]

    path.write_text("".join(lines), encoding="utf-8")
    print(f"ok {rel}")


def main() -> None:
    for rel, (created, updated, version) in FILES.items():
        apply(ROOT / rel, created, updated, version)


if __name__ == "__main__":
    main()
