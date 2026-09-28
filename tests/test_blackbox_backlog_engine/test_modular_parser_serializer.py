"""Blackbox tests verifying parser, serializer, and queue modular contracts."""

from pathlib import Path

from tools.backlog_engine.models import TaskStatus
from tools.backlog_engine.parser import FRONTMATTER_PATTERN, load_priority_map, parse_task_file
from tools.backlog_engine.queue import BacklogQueue
from tools.backlog_engine.serializer import write_task_file


def test_parser_extracts_all_frontmatter_metadata(tmp_path: Path):
    """Verifies that parse_task_file cleanly extracts all task properties and normalizes dependencies."""
    file = tmp_path / "0123-advanced-task.md"
    file.write_text(
        """---
id: '0123'
title: Advanced Modular Feature
status: Refined
dependencies: [42, TASK-0099]
governing_adrs: [ADR-0003, ADR-0007]
claimed_by: agent-007
branch: feat/agent-007
pr_url: https://github.com/runefoble/pr/123
---
# TASK-0123: Advanced Modular Feature

## Implementation Plan
1. Decompose parser and serializer.
2. Verify blackbox behavior.
""",
        encoding="utf-8",
    )

    task = parse_task_file(file, priority_rank=10)
    assert task.id == "0123"
    assert task.canonical_id == "TASK-0123"
    assert task.title == "Advanced Modular Feature"
    assert task.status == TaskStatus.READY
    assert task.dependencies == ["TASK-0042", "TASK-0099"]
    assert task.governing_adrs == ["ADR-0003", "ADR-0007"]
    assert task.claimed_by == "agent-007"
    assert task.branch == "feat/agent-007"
    assert task.pr_url == "https://github.com/runefoble/pr/123"
    assert task.priority_rank == 10
    assert "Implementation Plan" in task.body


def test_serializer_roundtrip_and_cleanup(tmp_path: Path):
    """Verifies write_task_file writes cleanly and cleans up branch/pr_url when released to ready."""
    file = tmp_path / "0050-test.md"
    file.write_text(
        "---\nid: '0050'\nstatus: in-progress\nclaimed_by: worker\nbranch: feat/50\n---\nBody\n"
    )

    task = parse_task_file(file)
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.claimed_by == "worker"

    # Transition to READY / released
    task.status = TaskStatus.READY
    task.claimed_by = None
    task.branch = None
    write_task_file(task)

    updated_task = parse_task_file(file)
    assert updated_task.status == TaskStatus.READY
    assert updated_task.claimed_by is None
    assert updated_task.branch is None
    assert "status: Refined" in file.read_text(encoding="utf-8")


def test_queue_integration_with_parser_and_serializer(tmp_path: Path):
    """Verifies BacklogQueue orchestrates state changes through parser and serializer."""
    backlog_dir = tmp_path / "backlog"
    for sub in ("complete", "refined", "proposed"):
        (backlog_dir / sub).mkdir(parents=True)

    t_file = backlog_dir / "refined" / "0005-integration.md"
    t_file.write_text("---\nid: 0005\ntitle: Integration\nstatus: Refined\n---\nBody\n")

    queue = BacklogQueue(backlog_dir)
    tasks = queue.list_all_tasks()
    assert len(tasks) == 1
    t = tasks[0]

    queue.claim_task(t, worker_id="stream-1", branch="feat/task-0005")
    reloaded = queue.list_all_tasks()[0]
    assert reloaded.status == TaskStatus.IN_PROGRESS
    assert reloaded.claimed_by == "stream-1"

    queue.release_task(reloaded)
    reloaded_after_release = queue.list_all_tasks()[0]
    assert reloaded_after_release.status == TaskStatus.READY
    assert reloaded_after_release.claimed_by is None


def test_load_priority_map_and_pattern(tmp_path: Path):
    """Verifies load_priority_map parses PRIORITY.md and FRONTMATTER_PATTERN matches."""
    priority_file = tmp_path / "PRIORITY.md"
    priority_file.write_text("1. **TASK-0010 (Refined)**: [`0010.md`](refined/0010.md)\n")
    ranks = load_priority_map(tmp_path)
    assert ranks == {"TASK-0010": 0}

    match = FRONTMATTER_PATTERN.match("---\nid: '0010'\n---\nBody")
    assert match is not None
