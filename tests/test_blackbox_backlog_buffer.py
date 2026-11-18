"""Backlog buffer, dependency, and registry invariants (TASK-0667).

These tests read the public backlog records: the lifecycle folders, the
frontmatter of each record, and the registry tables. They fail when the
ready buffer leaves the 6 to 12 band, when a refined task waits on a task
that is not complete, or when a registry disagrees with its record.
"""

from __future__ import annotations

import re
from pathlib import Path

from tools.project_visualizer.parsers.markdown_utils import parse_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG = REPO_ROOT / "docs" / "project" / "backlog"
PRODUCT = REPO_ROOT / "docs" / "project" / "product"
STORIES = REPO_ROOT / "docs" / "project" / "user_stories"

READY_BUFFER_MIN = 6
READY_BUFFER_MAX = 12


def _task_id(path: Path) -> str:
    match = re.search(r"(\d{4})", path.name)
    assert match, f"task file has no four-digit id: {path.name}"
    return match.group(1)


def _stage_by_task_id() -> dict[str, str]:
    stages: dict[str, str] = {}
    for stage in ("complete", "refined", "proposed"):
        for path in (BACKLOG / stage).glob("*.md"):
            stages[_task_id(path)] = stage
    return stages


def _dependency_ids(text: str) -> list[str]:
    frontmatter = text.split("---", 2)[1]
    block = frontmatter.split("dependencies:", 1)
    if len(block) < 2:
        return []
    deps: list[str] = []
    for line in block[1].splitlines()[1:]:
        if not line.startswith("- "):
            break
        match = re.match(r"- TASK-(\d{4})", line)
        if match:
            deps.append(match.group(1))
    return deps


def _registry_statuses(registry: Path, prefix: str, status_column: int) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in registry.read_text(encoding="utf-8").splitlines():
        if not line.startswith(f"| {prefix}-"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows[cells[0]] = cells[status_column]
    return rows


def _file_statuses(folder: Path, prefix: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for path in folder.glob("*.md"):
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        if "id" not in meta:
            continue
        statuses[f"{prefix}-{str(meta['id']).zfill(4)}"] = str(meta.get("status", ""))
    return statuses


def test_ready_buffer_holds_six_to_twelve_refined_tasks():
    """The refined folder holds between 6 and 12 tasks (the make prd-audit band)."""
    refined = list((BACKLOG / "refined").glob("*.md"))
    assert READY_BUFFER_MIN <= len(refined) <= READY_BUFFER_MAX, (
        f"refined buffer holds {len(refined)} tasks; expected {READY_BUFFER_MIN} "
        f"to {READY_BUFFER_MAX}"
    )


def test_refined_tasks_depend_only_on_complete_tasks():
    """A refined task waits on complete tasks only. Gaps must be demoted or sequenced."""
    stages = _stage_by_task_id()
    gaps: list[str] = []
    for path in (BACKLOG / "refined").glob("*.md"):
        for dep in _dependency_ids(path.read_text(encoding="utf-8")):
            dep_stage = stages.get(dep, "missing")
            if dep_stage != "complete":
                gaps.append(f"{_task_id(path)} -> {dep} ({dep_stage})")
    assert not gaps, "refined tasks depend on incomplete tasks: " + ", ".join(sorted(gaps))


def test_user_story_and_prd_registries_agree_with_record_status():
    """Each registry status matches the status in its record file."""
    mismatches: list[str] = []
    checks = (
        (
            STORIES / "REGISTRY.md",
            STORIES / "accepted",
            "US",
            4,
        ),
        (
            PRODUCT / "REGISTRY.md",
            PRODUCT / "accepted",
            "PRD",
            2,
        ),
    )
    for registry, folder, prefix, column in checks:
        registered = _registry_statuses(registry, prefix, column)
        recorded = _file_statuses(folder, prefix)
        for key in sorted(set(registered) | set(recorded)):
            if registered.get(key, "").lower() != recorded.get(key, "").lower():
                mismatches.append(
                    f"{key}: registry={registered.get(key)!r} record={recorded.get(key)!r}"
                )
    assert not mismatches, "registry and record disagree: " + "; ".join(mismatches)
