"""Tests for backlog queue ordering, dependency resolution, and cycle detection."""

from pathlib import Path

import pytest

from tools.backlog_engine.models import TaskStatus
from tools.backlog_engine.queue import BacklogQueue, load_priority_map


@pytest.fixture
def temp_backlog_dir(tmp_path: Path) -> Path:
    """Creates a temporary backlog directory structure for isolated testing."""
    backlog = tmp_path / "docs" / "project" / "backlog"
    for d in ("complete", "refined", "proposed"):
        (backlog / d).mkdir(parents=True)

    priority_content = """# Backlog Priority Index
1. **TASK-0001 (Complete)**: [`0001-task.md`](complete/0001-task.md)
2. **TASK-0002 (Refined)**: [`0002-task.md`](refined/0002-task.md)
3. **TASK-0003 (Refined)**: [`0003-task.md`](refined/0003-task.md)
"""
    (backlog / "PRIORITY.md").write_text(priority_content, encoding="utf-8")
    return backlog


def test_priority_queue_ordering(temp_backlog_dir: Path):
    """Verifies that unblocked tasks are ordered strictly according to PRIORITY.md rank."""
    ranks = load_priority_map(temp_backlog_dir)
    assert ranks["TASK-0001"] == 0
    assert ranks["TASK-0002"] == 1
    assert ranks["TASK-0003"] == 2

    # Create two ready tasks without dependencies
    t2 = temp_backlog_dir / "refined" / "0002-task.md"
    t2.write_text("---\nid: 0002\ntitle: Task 2\nstatus: Refined\n---\nBody", encoding="utf-8")
    t3 = temp_backlog_dir / "refined" / "0003-task.md"
    t3.write_text("---\nid: 0003\ntitle: Task 3\nstatus: Refined\n---\nBody", encoding="utf-8")

    queue = BacklogQueue(temp_backlog_dir)
    ready = queue.get_ready_unblocked_tasks()
    assert [t.canonical_id for t in ready] == ["TASK-0002", "TASK-0003"]


def test_dependency_resolution_blocks_and_unblocks(temp_backlog_dir: Path):
    """Verifies that tasks with unmet dependencies are blocked, while satisfied ones are ready."""
    t1 = temp_backlog_dir / "complete" / "0001-task.md"
    t1.write_text("---\nid: 0001\ntitle: Task 1\nstatus: Complete\n---\nBody", encoding="utf-8")

    t2 = temp_backlog_dir / "refined" / "0002-task.md"
    t2.write_text(
        "---\nid: 0002\ntitle: Task 2\nstatus: Refined\ndependencies: [TASK-0001]\n---\nBody",
        encoding="utf-8",
    )

    t3 = temp_backlog_dir / "refined" / "0003-task.md"
    t3.write_text(
        "---\nid: 0003\ntitle: Task 3\nstatus: Refined\ndependencies: [TASK-0002]\n---\nBody",
        encoding="utf-8",
    )

    queue = BacklogQueue(temp_backlog_dir)
    ready = queue.get_ready_unblocked_tasks()
    assert len(ready) == 1
    assert ready[0].canonical_id == "TASK-0002"


def test_circular_dependency_cycle_detection(temp_backlog_dir: Path):
    """Verifies that circular dependencies (A depends on B, B depends on A) block both tasks."""
    t2 = temp_backlog_dir / "refined" / "0002-task.md"
    t2.write_text(
        "---\nid: 0002\ntitle: Task 2\nstatus: Refined\ndependencies: [TASK-0003]\n---\nBody",
        encoding="utf-8",
    )
    t3 = temp_backlog_dir / "refined" / "0003-task.md"
    t3.write_text(
        "---\nid: 0003\ntitle: Task 3\nstatus: Refined\ndependencies: [TASK-0002]\n---\nBody",
        encoding="utf-8",
    )

    queue = BacklogQueue(temp_backlog_dir)
    ready = queue.get_ready_unblocked_tasks()
    assert len(ready) == 0


def test_unmet_external_dependency_blocks(temp_backlog_dir: Path):
    """Verifies that tasks with dependencies on nonexistent tasks remain blocked."""
    t2 = temp_backlog_dir / "refined" / "0002-task.md"
    t2.write_text(
        "---\nid: 0002\ntitle: Task 2\nstatus: Refined\ndependencies: [TASK-9999]\n---\nBody",
        encoding="utf-8",
    )

    queue = BacklogQueue(temp_backlog_dir)
    ready = queue.get_ready_unblocked_tasks()
    assert len(ready) == 0


def test_task_release_lifecycle(temp_backlog_dir: Path):
    """Verifies that release_task cleanly resets frontmatter on disk and re-enables readiness."""
    t2 = temp_backlog_dir / "refined" / "0002-task.md"
    t2.write_text("---\nid: 0002\ntitle: Task 2\nstatus: Refined\n---\nBody", encoding="utf-8")

    queue = BacklogQueue(temp_backlog_dir)
    task = queue.get_ready_unblocked_tasks()[0]

    queue.claim_task(task, worker_id="worker-release", branch="feat/task-0002")
    assert task.status == TaskStatus.IN_PROGRESS and len(queue.get_ready_unblocked_tasks()) == 0

    queue.release_task(task)
    assert task.status == TaskStatus.READY and task.claimed_by is None and task.branch is None

    disk_content = t2.read_text(encoding="utf-8")
    assert "claimed_by" not in disk_content and "status: Refined" in disk_content
    assert queue.get_ready_unblocked_tasks()[0].canonical_id == "TASK-0002"


def test_recover_stale_tasks(temp_backlog_dir: Path):
    """Verifies that recover_stale_tasks finds and releases orphaned in-progress tasks."""
    t2 = temp_backlog_dir / "refined" / "0002-task.md"
    t2.write_text(
        "---\nid: 0002\ntitle: Task 2\nstatus: in-progress\nclaimed_by: worker-old\nbranch: feat/old\n---\nBody",
        encoding="utf-8",
    )
    t3 = temp_backlog_dir / "refined" / "0003-task.md"
    t3.write_text(
        "---\nid: 0003\ntitle: Task 3\nstatus: in-progress\nclaimed_by: worker-old2\n---\nBody",
        encoding="utf-8",
    )
    t4 = temp_backlog_dir / "refined" / "0004-task.md"
    t4.write_text("---\nid: 0004\ntitle: Task 4\nstatus: Refined\n---\nBody", encoding="utf-8")

    queue = BacklogQueue(temp_backlog_dir)
    assert len(queue.get_ready_unblocked_tasks()) == 1

    recovered = queue.recover_stale_tasks()
    assert len(recovered) == 2
    assert {t.canonical_id for t in recovered} == {"TASK-0002", "TASK-0003"}
    assert len(queue.get_ready_unblocked_tasks()) == 3


def test_list_all_tasks_handles_missing_file_and_broken_symlinks(
    temp_backlog_dir: Path, monkeypatch
):
    """Verifies that list_all_tasks gracefully skips files that disappear concurrently or are broken symlinks."""
    t2 = temp_backlog_dir / "refined" / "0002-task.md"
    t2.write_text("---\nid: 0002\ntitle: Task 2\nstatus: Refined\n---\nBody", encoding="utf-8")

    # Create a broken symlink in proposed/
    import contextlib

    broken_symlink = temp_backlog_dir / "proposed" / "0076-missing-target.md"
    with contextlib.suppress(OSError):
        broken_symlink.symlink_to(temp_backlog_dir / "proposed" / "nonexistent.md")

    queue = BacklogQueue(temp_backlog_dir)

    # Also simulate a file being unlinked right between glob and parse_task_file
    import tools.backlog_engine.queue as queue_mod

    orig_parse = queue_mod.parse_task_file

    def flaky_parse(p: Path, priority_rank: int = 999999):
        if "simulated_missing" in p.name:
            raise FileNotFoundError(f"No such file: {p}")
        return orig_parse(p, priority_rank=priority_rank)

    monkeypatch.setattr(queue_mod, "parse_task_file", flaky_parse)

    fake_file = temp_backlog_dir / "proposed" / "0099-simulated_missing.md"
    fake_file.write_text(
        "---\nid: 0099\ntitle: Ghost\nstatus: Proposed\n---\nBody", encoding="utf-8"
    )

    # list_all_tasks should not raise FileNotFoundError
    tasks = queue.list_all_tasks()
    canonical_ids = [t.canonical_id for t in tasks]
    assert "TASK-0002" in canonical_ids
    assert "TASK-0099" not in canonical_ids


def test_list_all_tasks_deduplicates_across_lifecycle_folders(temp_backlog_dir: Path):
    """Verifies that tasks appearing in multiple folders are deduplicated, prioritizing higher states."""
    # Place same task in both refined/ and proposed/
    t2_refined = temp_backlog_dir / "refined" / "0002-task.md"
    t2_refined.write_text(
        "---\nid: 0002\ntitle: Task 2 Refined\nstatus: Refined\n---\nBody", encoding="utf-8"
    )

    t2_proposed = temp_backlog_dir / "proposed" / "0002-task.md"
    t2_proposed.write_text(
        "---\nid: 0002\ntitle: Task 2 Proposed\nstatus: Proposed\n---\nBody", encoding="utf-8"
    )

    queue = BacklogQueue(temp_backlog_dir)
    tasks = queue.list_all_tasks()

    matching = [t for t in tasks if t.canonical_id == "TASK-0002"]
    assert len(matching) == 1
    assert matching[0].status == TaskStatus.READY
    assert matching[0].title == "Task 2 Refined"


def test_get_completed_and_recover_stale_handles_missing_file(temp_backlog_dir: Path, monkeypatch):
    """Verifies get_completed_task_ids and recover_stale_tasks ignore disappearing files."""
    import tools.backlog_engine.queue as queue_mod

    def error_parse(p: Path, priority_rank: int = 999999):
        raise FileNotFoundError(f"Missing {p}")

    monkeypatch.setattr(queue_mod, "parse_task_file", error_parse)

    dummy = temp_backlog_dir / "complete" / "0001-task.md"
    dummy.write_text("dummy", encoding="utf-8")
    dummy_stale = temp_backlog_dir / "refined" / "0002-task.md"
    dummy_stale.write_text("dummy", encoding="utf-8")

    queue = BacklogQueue(temp_backlog_dir)
    assert queue.get_completed_task_ids() == set()
    assert queue.recover_stale_tasks() == []
