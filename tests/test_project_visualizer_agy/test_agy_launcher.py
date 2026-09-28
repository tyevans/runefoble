"""Tests for AGY launcher flag forwarding, command building, and GitHub Pages isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.project_visualizer.agy_runner import AgyRunnerManager
from tools.project_visualizer.generator import ProjectVisualizerGenerator


def test_agy_launcher_command_construction(repo_root: Path):
    runner = AgyRunnerManager(repo_root, agy_bin="/usr/bin/custom-agy")
    assert runner.find_agy_binary() == "/usr/bin/custom-agy"

    job1 = runner.launch_job("Refactor task", continue_session=False, target_entity_id="TASK-0100")
    assert job1.command == [
        "/usr/bin/custom-agy",
        "--dangerously-skip-permissions",
        "-p",
        "Refactor task",
    ]
    assert job1.target_entity_id == "TASK-0100" and job1.continue_session is False

    job2 = runner.launch_job("Continue task", continue_session=True)
    assert job2.command == [
        "/usr/bin/custom-agy",
        "--dangerously-skip-permissions",
        "-c",
        "-p",
        "Continue task",
    ]
    assert job2.continue_session is True


def test_agy_launcher_empty_prompt_validation(repo_root: Path):
    runner = AgyRunnerManager(repo_root)
    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        runner.launch_job("   ")


def test_agy_launcher_binary_resolution(repo_root: Path, monkeypatch: pytest.MonkeyPatch):
    runner = AgyRunnerManager(repo_root)
    monkeypatch.setattr("shutil.which", lambda _: "/opt/bin/agy")
    assert runner.find_agy_binary() == "/opt/bin/agy"

    monkeypatch.setattr("shutil.which", lambda _: None)
    monkeypatch.setattr("pathlib.Path.exists", lambda _: False)
    assert runner.find_agy_binary() == "agy"


def test_static_build_strict_github_pages_isolation(repo_root: Path, tmp_path: Path):
    """Verify AGY launcher UI, modal, and scripts are strictly isolated to live dev server."""
    generator = ProjectVisualizerGenerator(repo_root)

    # Static build: zero AGY elements in published bundle for GitHub Pages
    static_bundle = generator.build_file(tmp_path / "project-visualizer.html", is_live_server=False)
    static_html = static_bundle.read_text(encoding="utf-8")
    for elem in [
        "agy-header-btn",
        "agy-modal",
        "// --- agy/agy_modal.js ---",
        "// --- agy/agy_presets.js ---",
        "// --- agy/agy_runner.js ---",
        "// --- agy_launcher.js ---",
        "Launch AGY",
    ]:
        assert elem not in static_html
    assert "window.IS_LIVE_SERVER = false;" in static_html

    # Live server build: AGY elements present
    live_html = generator.generate_html(is_live_server=True)
    for elem in [
        "agy-header-btn",
        "agy-modal",
        "// --- agy/agy_modal.js ---",
        "// --- agy/agy_presets.js ---",
        "// --- agy/agy_runner.js ---",
        "// --- agy_launcher.js ---",
        "Launch AGY",
    ]:
        assert elem in live_html
    assert "window.IS_LIVE_SERVER = true;" in live_html


def test_agy_launcher_module_decomposition_architecture(repo_root: Path):
    """Verify AGY submodules under agy/ adhere to Hard Invariant 6 and DoD line limits."""
    agy_dir = repo_root / "tools" / "project_visualizer" / "static" / "js" / "agy"
    assert agy_dir.is_dir(), "tools/project_visualizer/static/js/agy/ must exist"

    expected_submodules = {
        "agy_modal.js": 140,
        "agy_presets.js": 140,
        "agy_runner.js": 140,
    }
    for filename, limit in expected_submodules.items():
        file_path = agy_dir / filename
        assert file_path.is_file(), f"Expected submodule {filename} does not exist"
        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        assert line_count < limit, f"{filename} must be < {limit} lines, got {line_count}"

    facade_path = repo_root / "tools" / "project_visualizer" / "static" / "js" / "agy_launcher.js"
    assert facade_path.is_file(), "Facade agy_launcher.js must exist"
    facade_lines = len(facade_path.read_text(encoding="utf-8").splitlines())
    assert facade_lines < 50, f"Facade agy_launcher.js must be < 50 lines, got {facade_lines}"
