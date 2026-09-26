"""Tests for PRD creation, maintenance, and task decomposition pipeline."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.prd_pipeline.cli import main
from tools.prd_pipeline.decomposer import PRDDecomposer
from tools.prd_pipeline.models import SliceType
from tools.prd_pipeline.prd_manager import PRDManager
from tools.prd_pipeline.registry_sync import RegistrySynchronizer
from tools.prd_pipeline.writer import PlanWriter


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


def test_prd_manager_lifecycle_and_creation(temp_project: Path):
    mgr = PRDManager(temp_project)
    assert mgr.get_next_prd_number() == 1

    prd = mgr.create_prd(
        title="Alchemical Laboratory",
        persona="Bram the Tinkerer",
        target_bc="character_sheet",
        summary="Need for interactive potion brewing.",
        status="Accepted",
    )
    assert prd.canonical_id == "PRD-0001"
    assert prd.title == "Alchemical Laboratory"
    assert prd.file_path.exists()
    assert "Who this is for" in prd.body
    assert mgr.get_next_prd_number() == 2


def test_prd_audit_detects_buffer_and_undecomposed(temp_project: Path):
    mgr = PRDManager(temp_project)
    prd = mgr.create_prd(
        title="Tactile Terrain",
        persona="Evelyn",
        target_bc="board_state",
        summary="Terrain rules.",
        status="Accepted",
    )

    audit = mgr.audit_prds()
    assert audit["total_prds"] == 1
    assert prd.canonical_id in audit["undecomposed_prds"]
    assert audit["buffer"]["ready_buffer_low"] is True


def test_decomposer_generates_spikes_and_vertical_slices(temp_project: Path):
    mgr = PRDManager(temp_project)
    prd = mgr.create_prd(
        title="3D Relic WebGL Canvas Inspector",
        persona="Rowan the Artisan",
        target_bc="campaign_lore",
        summary="Need 3D WebGL rotation and wax seal interactions.",
        status="Accepted",
        outcomes=[
            "1. 3D WebGL relic canvas renders with 60fps.",
            "2. Wax seal breaking publishes real-time WebSocket domain event.",
        ],
    )

    decomposer = PRDDecomposer(temp_project)
    plan = decomposer.plan_decomposition(prd)

    # Should detect 3D / WebGL keyword and create an architectural spike
    assert len(plan.spikes) == 1
    spike = plan.spikes[0]
    assert spike.is_spike is True
    assert "SPIKE:" in spike.title
    assert spike.slice_type == SliceType.SPIKE

    # Should have vertical slices: Domain, API, UI, Worker
    slice_types = [s.slice_type for s in plan.slices]
    assert SliceType.DOMAIN_AGGREGATE in slice_types
    assert SliceType.API_AUTH in slice_types
    assert SliceType.MICROFRONTEND in slice_types

    # Verify INVEST criteria and single agy pass sizing
    for t in plan.all_tasks:
        assert "Small" in t.invest_evaluation
        assert "500 lines" in t.invest_evaluation["Small"]
        assert len(t.definition_of_done) > 0


def test_plan_writer_persists_tasks_and_stories(temp_project: Path):
    mgr = PRDManager(temp_project)
    prd = mgr.create_prd(
        title="Campfire Storytelling",
        persona="Marcus",
        target_bc="game_session",
        summary="Rest banter.",
        status="Accepted",
    )

    decomposer = PRDDecomposer(temp_project)
    plan = decomposer.plan_decomposition(prd)
    writer = PlanWriter(temp_project)

    for task in plan.all_tasks:
        fp = writer.write_task(task)
        assert fp.exists()
        content = fp.read_text(encoding="utf-8")
        assert f"# {task.canonical_id}:" in content
        assert "Definition of Done (Hard Invariant 7" in content

    for story in plan.stories:
        sp = writer.write_user_story(story)
        assert sp.exists()
        s_content = sp.read_text(encoding="utf-8")
        assert f"# {story.canonical_id}" in s_content
        assert "As a" in s_content


def test_registry_synchronizer_repairs_stale_links_and_indexes(temp_project: Path):
    mgr = PRDManager(temp_project)
    prd = mgr.create_prd(
        title="Downtime Alchemy",
        persona="Bram",
        target_bc="character_sheet",
        summary="Crafting reagents.",
        status="Accepted",
    )

    decomposer = PRDDecomposer(temp_project)
    plan = decomposer.plan_decomposition(prd)
    writer = PlanWriter(temp_project)

    written_tasks = []
    for t in plan.all_tasks:
        fp = writer.write_task(t)
        written_tasks.append((t.canonical_id, t.title, f"../../backlog/proposed/{fp.name}"))

    mgr.update_prd_links(prd, written_tasks)

    # Sync registries
    sync = RegistrySynchronizer(temp_project)
    res = sync.sync_all()

    assert res["prds_synced"] == 1
    assert res["tasks_synced"] >= len(plan.all_tasks)

    # Check PRIORITY.md contains all tasks
    priority_content = (temp_project / "docs" / "project" / "backlog" / "PRIORITY.md").read_text(
        encoding="utf-8"
    )
    for t in plan.all_tasks:
        assert t.canonical_id in priority_content


def test_cli_execution(temp_project: Path, monkeypatch: pytest.MonkeyPatch):
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

    # CLI decompose
    code = main(["decompose", "--prd", "PRD-0001", "--plan-only"])
    assert code == 0

    code = main(["decompose", "--prd", "PRD-0001"])
    assert code == 0

    # CLI prompt
    code = main(["prompt", "--prd", "PRD-0001"])
    assert code == 0

    # CLI sync
    code = main(["sync"])
    assert code == 0


def test_shell_script_interface():
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "decompose-prds.sh"
    assert script.exists()

    result = subprocess.run([str(script), "audit"], capture_output=True, text=True, cwd=repo_root)
    assert result.returncode == 0
    assert "Runefoble PRD & Backlog Audit" in result.stdout
