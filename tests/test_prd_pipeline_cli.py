"""Tests for PRD pipeline CLI execution, error exits, and shell scripts."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.prd_pipeline.cli import main


def test_cli_execution(temp_project: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies end-to-end CLI subcommands: audit, create, decompose, prompt, and sync."""
    monkeypatch.chdir(temp_project)

    # CLI audit on fresh project
    code = main(["audit"])
    assert code == 0

    # CLI create PRD
    code = main(
        [
            "create",
            "--title",
            "Spectator Studio 2",
            "--persona",
            "Devon",
            "--bc",
            "audience_studio",
            "--summary",
            "Interactive polls.",
        ]
    )
    assert code == 0

    # CLI decompose plan-only
    code = main(["decompose", "--prd", "PRD-0001", "--plan-only"])
    assert code == 0

    # CLI decompose execute
    code = main(["decompose", "--prd", "PRD-0001"])
    assert code == 0

    # CLI prompt
    code = main(["prompt", "--prd", "PRD-0001"])
    assert code == 0

    # CLI sync
    code = main(["sync"])
    assert code == 0


def test_cli_decompose_all_and_error_exits(temp_project: Path, monkeypatch: pytest.MonkeyPatch):
    """Verifies CLI error exits on missing PRD IDs and decompose-all functionality."""
    monkeypatch.chdir(temp_project)

    # Decompose non-existent PRD should return exit code 1
    code = main(["decompose", "--prd", "PRD-9999"])
    assert code == 1

    # Prompt non-existent PRD should return exit code 1
    code = main(["prompt", "--prd", "PRD-9999"])
    assert code == 1

    # Create a PRD and test decompose-all
    main(
        [
            "create",
            "--title",
            "Chaos Arena",
            "--persona",
            "Devon",
            "--bc",
            "audience_studio",
            "--summary",
            "Live polls.",
        ]
    )
    code = main(["decompose-all", "--plan-only"])
    assert code == 0


def test_shell_script_interface():
    """Verifies that the shell script entrypoint scripts/decompose-prds.sh works."""
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "decompose-prds.sh"
    assert script.exists()

    result = subprocess.run([str(script), "audit"], capture_output=True, text=True, cwd=repo_root)
    assert result.returncode == 0
    assert "Runefoble PRD & Backlog Audit" in result.stdout
