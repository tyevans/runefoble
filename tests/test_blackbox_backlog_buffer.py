"""Backlog buffer warnings and registry agreement (TASK-0667).

The buffer band (6 to 12 refined tasks) and the dependency rule (a refined task waits
on complete tasks only) are curation warnings. `scripts/check_backlog_links.py` prints
them and keeps its exit status. The orchestrator demotes tasks by judgement.

These tests run the check as a process against fixture backlogs in `tmp_path`, and
they check that each registry agrees with the status of its record file.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tools.project_visualizer.parsers.markdown_utils import parse_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKLOG = REPO_ROOT / "docs" / "project" / "backlog"
PRODUCT = REPO_ROOT / "docs" / "project" / "product"
STORIES = REPO_ROOT / "docs" / "project" / "user_stories"
SCRIPTS = REPO_ROOT / "scripts"
FIXTURE_SCRIPTS = ("check_backlog_links.py", "backlog_records.py")


def _fixture_repo(
    root: Path, refined: dict[str, list[str]], complete: tuple[str, ...] = ()
) -> None:
    """Write a fixture repository with refined tasks and the complete tasks they may cite.

    `refined` maps a refined task id to the dependency ids it lists.
    """
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for name in FIXTURE_SCRIPTS:
        (scripts / name).write_text((SCRIPTS / name).read_text(encoding="utf-8"), encoding="utf-8")
    for stage, ids in (("refined", refined), ("complete", {c: [] for c in complete})):
        folder = root / "docs" / "project" / "backlog" / stage
        folder.mkdir(parents=True)
        for task_id, deps in ids.items():
            dep_lines = "".join(f"- TASK-{dep}\n" for dep in deps)
            deps_block = f"dependencies:\n{dep_lines}" if deps else "dependencies: []\n"
            governance = "governing_adrs: []\ngoverning_prds: []\ngoverning_stories: []\n"
            (folder / f"{task_id}-fixture-task.md").write_text(
                f"---\nid: '{task_id}'\ntitle: Fixture {task_id}\nstatus: {stage.title()}\n"
                f"{governance}{deps_block}---\n\n# TASK-{task_id}: Fixture\n",
                encoding="utf-8",
            )


def _run_check(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "check_backlog_links.py")],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_over_buffered_refined_folder_prints_warning_and_keeps_exit_status(tmp_path: Path):
    """Thirteen refined tasks print a band warning. The check still exits 0."""
    refined = {f"{n:04d}": [] for n in range(1, 14)}
    _fixture_repo(tmp_path, refined)

    result = _run_check(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "warning refined_buffer: refined buffer holds 13 tasks; above 12" in result.stdout


def test_dependency_gap_prints_one_warning_per_gap_and_keeps_exit_status(tmp_path: Path):
    """A refined task that waits on a refined task prints a dependency warning. Exit 0."""
    refined = {f"{n:04d}": [] for n in range(2, 8)}
    refined["0002"] = ["0001"]  # 0001 is complete: no warning
    refined["0003"] = ["0009"]  # 0009 is absent from every folder: warning
    _fixture_repo(tmp_path, refined, complete=("0001",))

    result = _run_check(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "warning dependency_gap: 0003-fixture-task.md: depends on TASK-0009 (missing)" in (
        result.stdout
    )
    assert "depends on TASK-0001" not in result.stdout


def test_buffer_inside_band_with_complete_dependencies_prints_no_warning(tmp_path: Path):
    """Six refined tasks that wait on complete tasks produce no curation warning."""
    refined = {f"{n:04d}": [] for n in range(2, 8)}
    refined["0002"] = ["0001"]
    _fixture_repo(tmp_path, refined, complete=("0001",))

    result = _run_check(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "warning" not in result.stdout


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
