"""Shared helpers for backlog record checks and repairs (TASK-0666).

The checker (`check_backlog_links.py`) and the repair script (`fix_backlog_records.py`)
both read records through these helpers so that they agree on what counts as a
dead link, a body-status mismatch, or an unresolved repository path.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKLOG_DIR = REPO_ROOT / "docs" / "project" / "backlog"
PRODUCT_DIR = REPO_ROOT / "docs" / "project" / "product"
STORIES_DIR = REPO_ROOT / "docs" / "project" / "user_stories"
ADR_DIR = REPO_ROOT / "docs" / "project" / "adrs" / "accepted"

MD_LINK = re.compile(r"\]\(([^)\s]+)\)")
BACKTICK = re.compile(r"`([^`\s]+)`")
LINE_SUFFIX = re.compile(r":\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*$")
# A complete record marks a cited path that no longer exists: removed later, or planned and never
# created because the work landed elsewhere.
REMOVED_MARKS = (" (removed)", " (not created)")
REPO_TOPS = (
    "libs/",
    "services/",
    "gateway/",
    "frontend/",
    "tests/",
    "docs/",
    "scripts/",
    "deployments/",
    "e2e/",
    "tools/",
    ".github/",
)
GOVERNANCE_KEYS = ("governing_prds", "governing_stories", "governing_adrs", "dependencies")
ACTIVE_STAGES = ("refined", "proposed")


def task_id_of(path: Path) -> str:
    """Return the four-digit task id from a file name such as `0666-slug.md`."""
    return path.name.split("-", 1)[0]


def split_record(text: str) -> tuple[dict, str]:
    """Return the parsed frontmatter mapping and the body text of a record."""
    _, front, body = text.split("---", 2)
    return yaml.safe_load(front) or {}, body


def frontmatter_bounds(lines: list[str]) -> tuple[int, int]:
    """Return the indexes of the opening and closing frontmatter delimiters."""
    if not lines or lines[0].strip() != "---":
        raise ValueError("record has no opening frontmatter delimiter")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return 0, index
    raise ValueError("record has no closing frontmatter delimiter")


def status_section_index(lines: list[str]) -> int | None:
    """Return the index of the first non-empty line under `## Status`, if any."""
    for index, line in enumerate(lines):
        if line.strip() == "## Status":
            for cursor in range(index + 1, len(lines)):
                if lines[cursor].strip():
                    return cursor
                if lines[cursor].startswith("## "):
                    return None
            return None
    return None


def iter_markdown_links(text: str) -> Iterator[str]:
    """Yield every local markdown link target (without URL fragments)."""
    for match in MD_LINK.finditer(text):
        target = match.group(1)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        local = target.split("#", 1)[0]
        if local:
            yield local


def repo_path_tokens(text: str) -> Iterator[tuple[re.Match, str, bool]]:
    """Yield (match, repository path, already-marked-removed) for cited repo paths.

    Only backticked tokens that start with a known repository top-level directory
    and name a file (or a directory with a trailing slash) are considered.
    Placeholders such as `services/<bc>/` and globs are skipped.
    """
    for match in BACKTICK.finditer(text):
        token = match.group(1).rstrip(".,;:)")
        path = LINE_SUFFIX.sub("", token)
        if not path.startswith(REPO_TOPS):
            continue
        if any(char in path for char in "<>*{}$"):
            continue
        if "." not in path.rsplit("/", 1)[-1] and not path.endswith("/"):
            continue
        removed = text[match.end() :].startswith(REMOVED_MARKS)
        yield match, path, removed


def path_exists(path: str) -> bool:
    return (REPO_ROOT / path.rstrip("/")).exists()


def tracked_files() -> list[str]:
    """Return the git-tracked file list of the repository (read-only)."""
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def complete_records() -> list[Path]:
    return sorted((BACKLOG_DIR / "complete").glob("*.md"))


def active_records() -> list[Path]:
    files: list[Path] = []
    for stage in ACTIVE_STAGES:
        files.extend(sorted((BACKLOG_DIR / stage).glob("*.md")))
    return files


def registry_ids(directory: Path, prefix: str) -> set[str]:
    """Return IDs such as `PRD-0001` for files named `prd-0001-*.md` below a directory."""
    found: set[str] = set()
    for path in directory.rglob(f"{prefix.lower()}-*.md"):
        found.add(f"{prefix.upper()}-{path.name.split('-')[1]}")
    return found
