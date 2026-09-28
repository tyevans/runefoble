"""Fixtures for blackbox backlog engine testing."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def mock_backlog_repo(tmp_path: Path) -> Path:
    """Initializes a full mock git repository with backlog structure and sample tasks."""
    subprocess.run(["git", "init", "-b", "main"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    backlog_dir = tmp_path / "docs" / "project" / "backlog"
    for sub in ("complete", "refined", "proposed"):
        (backlog_dir / sub).mkdir(parents=True)

    priority_content = """# Backlog Priority Index
1. **TASK-0001 (Complete)**: [`0001-task.md`](complete/0001-task.md)
2. **TASK-0002 (Refined)**: [`0002-task.md`](refined/0002-task.md)
3. **TASK-0003 (Refined)**: [`0003-task.md`](refined/0003-task.md)
4. **TASK-0004 (Proposed)**: [`0004-task.md`](proposed/0004-task.md)
"""
    (backlog_dir / "PRIORITY.md").write_text(priority_content, encoding="utf-8")

    t1 = backlog_dir / "complete" / "0001-task.md"
    t1.write_text(
        "---\nid: '0001'\ntitle: Foundation Setup\nstatus: Complete\n---\n# TASK-0001\nDone.\n",
        encoding="utf-8",
    )

    t2 = backlog_dir / "refined" / "0002-task.md"
    t2.write_text(
        "---\nid: '0002'\ntitle: Core Parsing\nstatus: Refined\ndependencies: [TASK-0001]\n---\n# TASK-0002\nReady task.\n",
        encoding="utf-8",
    )

    t3 = backlog_dir / "refined" / "0003-task.md"
    t3.write_text(
        "---\nid: '0003'\ntitle: Blocked Task\nstatus: Refined\ndependencies: [TASK-0002]\n---\n# TASK-0003\nBlocked.\n",
        encoding="utf-8",
    )

    t4 = backlog_dir / "proposed" / "0004-task.md"
    t4.write_text(
        "---\nid: '0004'\ntitle: Future Feature\nstatus: Proposed\n---\n# TASK-0004\nProposed.\n",
        encoding="utf-8",
    )

    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial mock backlog"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    return tmp_path
