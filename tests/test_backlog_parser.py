"""Tests for backlog task markdown and YAML frontmatter parsing."""

from pathlib import Path

from tools.backlog_engine.models import Task, TaskStatus
from tools.backlog_engine.queue import parse_task_file, write_task_file


def test_parse_task_file_octal_safety(tmp_path: Path):
    """Ensures leading-zero task IDs are not parsed as octal integers."""
    refined_dir = tmp_path / "refined"
    refined_dir.mkdir()
    task_file = refined_dir / "0024-sample-task.md"
    content = """---
id: 0024
title: Sample Octal Safety Task
status: Refined
dependencies: [TASK-0001]
governing_adrs: [ADR-0001]
---

# TASK-0024: Sample Octal Safety Task
Description here.
"""
    task_file.write_text(content, encoding="utf-8")

    task = parse_task_file(task_file, priority_rank=1)
    assert task.id == "0024"
    assert task.canonical_id == "TASK-0024"
    assert task.status == TaskStatus.READY
    assert task.dependencies == ["TASK-0001"]


def test_parse_task_file_yaml_schema_and_adrs(tmp_path: Path):
    """Validates frontmatter YAML schema parsing, dep normalization, and ADR citations."""
    task_file = tmp_path / "0046-schema-task.md"
    content = """---
id: '0046'
title: Schema Validation Task
status: in-progress
dependencies: [1, TASK-0002]
governing_adrs: [ADR-0007, ADR-0008, ADR-0009]
claimed_by: worker-test
branch: feat/0046-test
pr_url: https://github.com/example/pr/46
---

# TASK-0046: Schema Validation Task
Specification details.
"""
    task_file.write_text(content, encoding="utf-8")

    task = parse_task_file(task_file, priority_rank=46)
    assert task.id == "0046"
    assert task.canonical_id == "TASK-0046"
    assert task.title == "Schema Validation Task"
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.dependencies == ["TASK-0001", "TASK-0002"]
    assert task.governing_adrs == ["ADR-0007", "ADR-0008", "ADR-0009"]
    assert task.claimed_by == "worker-test"
    assert task.branch == "feat/0046-test"
    assert task.pr_url == "https://github.com/example/pr/46"
    assert task.priority_rank == 46


def test_parse_task_file_dod_and_title_fallback(tmp_path: Path):
    """Verifies fallback title extraction from H1 header and DoD section preservation."""
    task_file = tmp_path / "0030-sample.md"
    content = """---
status: Refined
---

# TASK-0030: Fallback Title From Markdown

## Definition of Done (Hard Invariant 7)
1. Verify frontdoor blackbox test suite passes.
2. Ensure DoD checklist items are fully captured.
"""
    task_file.write_text(content, encoding="utf-8")

    task = parse_task_file(task_file)
    assert task.id == "0030"
    assert task.canonical_id == "TASK-0030"
    assert task.title == "TASK-0030: Fallback Title From Markdown"
    assert "Definition of Done (Hard Invariant 7)" in task.body
    assert "Verify frontdoor blackbox test suite passes." in task.body


def test_parse_task_file_status_inference_and_malformed_yaml(tmp_path: Path):
    """Verifies directory-based status inference and resilience to malformed YAML."""
    complete_dir = tmp_path / "complete"
    proposed_dir = tmp_path / "proposed"
    complete_dir.mkdir()
    proposed_dir.mkdir()

    # Malformed YAML falls back gracefully and infers COMPLETE from directory
    t1_file = complete_dir / "0001-broken.md"
    t1_file.write_text("---\n: invalid: [yaml :---\n# TASK-0001\nBody", encoding="utf-8")
    t1 = parse_task_file(t1_file)
    assert t1.id == "0001"
    assert t1.status == TaskStatus.COMPLETE

    # Missing status in proposed directory infers PROPOSED
    t2_file = proposed_dir / "0005-idea.md"
    t2_file.write_text("---\nid: '0005'\ntitle: Idea Task\n---\nBody", encoding="utf-8")
    t2 = parse_task_file(t2_file)
    assert t2.status == TaskStatus.PROPOSED


def test_write_task_file_roundtrip(tmp_path: Path):
    """Verifies write_task_file updates frontmatter on disk while preserving body."""
    task_file = tmp_path / "0012-write-test.md"
    task_file.write_text(
        "---\nid: '0012'\ntitle: Initial Title\nstatus: Refined\n---\nInitial Body Content.\n",
        encoding="utf-8",
    )

    task = Task(
        id="0012",
        title="Updated Title",
        status=TaskStatus.COMPLETE,
        file_path=task_file,
        dependencies=["TASK-0001"],
        governing_adrs=["ADR-0005"],
        body="Initial Body Content.\n",
    )
    write_task_file(task)

    updated_text = task_file.read_text(encoding="utf-8")
    assert "status: Complete" in updated_text
    assert "title: Updated Title" in updated_text
    assert "TASK-0001" in updated_text
    assert "ADR-0005" in updated_text
    assert "Initial Body Content." in updated_text
