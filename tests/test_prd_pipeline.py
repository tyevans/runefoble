"""Tests for PRD creation, maintenance, and task decomposition pipeline."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tools.prd_pipeline.cli import main
from tools.prd_pipeline.decomposer import PRDDecomposer
from tools.prd_pipeline.models import SliceType
from tools.prd_pipeline.planner import (
    DecompositionPlanner,
    requires_architectural_spike,
    requires_ui_component,
    requires_worker_slice,
)
from tools.prd_pipeline.prd_manager import PRDManager
from tools.prd_pipeline.registry_sync import RegistrySynchronizer
from tools.prd_pipeline.templates import (
    create_user_story_draft,
    format_task_markdown,
    format_user_story_markdown,
    render_acceptance_criteria,
    serialize_yaml_list,
)
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


def test_decomposer_execute_and_counters(temp_project: Path):
    """Verifies execute_decomposition and counter resolution on PRDDecomposer facade."""
    mgr = PRDManager(temp_project)
    prd = mgr.create_prd(
        title="Arcane Telemetry",
        persona="Lyra",
        target_bc="campaign_analytics",
        summary="Telemetry pipeline for dice events.",
        status="Accepted",
    )
    decomposer = PRDDecomposer(temp_project)

    # Initial counters
    assert decomposer.get_max_task_number() == 1  # 0001-bootstrap exists
    assert decomposer.get_max_story_number() == 0

    # Execute decomposition via PRD directly
    res = decomposer.execute_decomposition(prd)
    assert len(res["tasks"]) >= 2
    assert len(res["stories"]) == 1
    for p in res["tasks"] + res["stories"]:
        assert p.exists()

    # Counter should update
    new_max = decomposer.get_max_task_number()
    assert new_max > 1

    # Execute with plan object directly
    plan = decomposer.plan_decomposition(prd)
    res_plan = decomposer.execute_decomposition(plan)
    assert len(res_plan["tasks"]) == len(plan.all_tasks)


def test_planner_heuristics_and_dependencies(temp_project: Path):
    """Directly tests planner heuristics and slice sequencing."""
    mgr = PRDManager(temp_project)

    # Spike keywords check
    prd_spike = mgr.create_prd(
        title="3D Canvas Relic",
        persona="Artisan",
        target_bc="campaign_lore",
        summary="Requires 3D WebGL meshes.",
        status="Accepted",
    )
    assert requires_architectural_spike(prd_spike) is True
    assert requires_ui_component(prd_spike) is True

    prd_plain = mgr.create_prd(
        title="Dice Roller Engine",
        persona="Adventurer",
        target_bc="game_session",
        summary="Standard roll logic.",
        status="Accepted",
    )
    assert requires_architectural_spike(prd_plain) is False

    # UI and Worker heuristics
    prd_worker = mgr.create_prd(
        title="Stream Listener",
        persona="Watcher",
        target_bc="game_session",
        summary="Redis stream websocket broadcast.",
        status="Accepted",
    )
    assert requires_worker_slice(prd_worker) is True

    # Planner direct execution with offset numbers
    planner = DecompositionPlanner(current_task_num=50, current_story_num=10)
    plan = planner.plan(prd_spike)
    assert plan.spikes[0].number == 51
    assert plan.stories[0].number == 11
    # Check dependencies: domain aggregate depends on spike
    domain_slice = next(s for s in plan.slices if s.slice_type == SliceType.DOMAIN_AGGREGATE)
    assert domain_slice.dependencies == [plan.spikes[0].canonical_id]
    # API slice depends on domain slice
    api_slice = next(s for s in plan.slices if s.slice_type == SliceType.API_AUTH)
    assert api_slice.dependencies == [domain_slice.canonical_id]


def test_templates_formatting_and_helpers(temp_project: Path):
    """Directly tests template formatting functions and metadata serialization."""
    # YAML serialization
    assert serialize_yaml_list([]) == "[]"
    assert serialize_yaml_list(["ADR-0001", "ADR-0002"]) == "- ADR-0001\n- ADR-0002"

    # Criteria rendering
    assert render_acceptance_criteria(["First", "Second"]) == "1. First\n2. Second"

    mgr = PRDManager(temp_project)
    prd = mgr.create_prd(
        title="Potion Mixing",
        persona="Alchemist",
        target_bc="character_sheet",
        summary="Reagent mixing mechanics.",
        status="Accepted",
    )

    story = create_user_story_draft("US-0099", 99, prd)
    assert story.persona == "Alchemist"
    story_md = format_user_story_markdown(story)
    assert "# US-0099 — Potion Mixing Experience" in story_md
    assert "**As a** Alchemist" in story_md

    decomposer = PRDDecomposer(temp_project)
    plan = decomposer.plan_decomposition(prd)
    task_md = format_task_markdown(plan.slices[0])
    assert f"# {plan.slices[0].canonical_id}:" in task_md
    assert "## INVEST Criteria Evaluation" in task_md
    assert "## Definition of Done (Hard Invariant 7" in task_md


def test_decomposer_backward_compatibility_delegates(temp_project: Path):
    """Verifies that private helper delegates remain functional on PRDDecomposer."""
    mgr = PRDManager(temp_project)
    prd = mgr.create_prd(
        title="Interactive Canvas",
        persona="Player",
        target_bc="board_state",
        summary="Canvas UI component.",
        status="Accepted",
    )
    decomposer = PRDDecomposer(temp_project)

    assert decomposer._requires_ui_component(prd) is True
    assert decomposer._requires_architectural_spike(prd) is False

    from tools.prd_pipeline.models import PRD

    plain_prd = PRD(
        id="PRD-0999",
        number=999,
        title="Static Card Layout",
        status="Accepted",
        created="2026-09-26",
        file_path=Path("/tmp/prd.md"),
        who_for="Player",
        problem_statement="",
        good_looks_like="",
        does_not_do="",
        costs_at_scale="",
        checkable_outcomes=[],
        linked_stories=[],
        implementing_tasks=[],
        raw_frontmatter={},
        body="Purely static visual layout without background processing.",
        target_bc="board_state",
    )
    assert decomposer._requires_worker_slice(plain_prd) is False

    spike = decomposer._create_spike_draft("TASK-0999", 999, prd, "board_state")
    assert spike.canonical_id == "TASK-0999"
    assert spike.is_spike is True

    domain = decomposer._create_domain_slice_draft("TASK-1000", 1000, prd, "board_state", [], [])
    assert domain.slice_type == SliceType.DOMAIN_AGGREGATE

    api = decomposer._create_api_slice_draft("TASK-1001", 1001, prd, "board_state", [], [])
    assert api.slice_type == SliceType.API_AUTH

    ui = decomposer._create_ui_slice_draft("TASK-1002", 1002, prd, "board_state", [], [])
    assert ui.slice_type == SliceType.MICROFRONTEND

    worker = decomposer._create_worker_slice_draft("TASK-1003", 1003, prd, "board_state", [], [])
    assert worker.slice_type == SliceType.WORKER_INTEGRATION
