"""Fixtures for PRD pipeline testing."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Creates a temporary project structure mirroring docs/project."""
    repo = tmp_path / "repo"
    repo.mkdir()

    # Structure
    (repo / "docs" / "project" / "product" / "accepted").mkdir(parents=True)
    (repo / "docs" / "project" / "product" / "shipped").mkdir(parents=True)
    (repo / "docs" / "project" / "user_stories" / "accepted").mkdir(parents=True)
    (repo / "docs" / "project" / "backlog" / "proposed").mkdir(parents=True)
    (repo / "docs" / "project" / "backlog" / "refined").mkdir(parents=True)
    (repo / "docs" / "project" / "backlog" / "complete").mkdir(parents=True)

    # Initial registries
    (repo / "docs" / "project" / "product" / "REGISTRY.md").write_text(
        "# Product Requirement Record (PRD) Registry\n\n| ID | Title | Status | Date | File |\n|---|---|---|---|---|\n",
        encoding="utf-8",
    )
    (repo / "docs" / "project" / "user_stories" / "REGISTRY.md").write_text(
        "# User Story Registry\n\n| ID | Title | Persona | PRD | Status | File |\n|---|---|---|---|---|---|\n",
        encoding="utf-8",
    )
    (repo / "docs" / "project" / "backlog" / "PRIORITY.md").write_text(
        "# Backlog Priority Index\n\n1. **TASK-0001 (Complete)**: [`0001-bootstrap.md`](complete/0001-bootstrap.md) — Bootstrap\n",
        encoding="utf-8",
    )

    # Dummy complete task
    (repo / "docs" / "project" / "backlog" / "complete" / "0001-bootstrap.md").write_text(
        "---\nid: '0001'\ntitle: Bootstrap\nstatus: Complete\n---\n# TASK-0001: Bootstrap\n",
        encoding="utf-8",
    )

    return repo
