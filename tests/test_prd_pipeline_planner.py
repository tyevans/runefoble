"""Tests for PRD decomposition planner, heuristics, and slice analysis."""

from __future__ import annotations

from pathlib import Path

from tools.prd_pipeline.decomposer import PRDDecomposer
from tools.prd_pipeline.models import PRD, SliceType
from tools.prd_pipeline.planner import (
    DecompositionPlanner,
    requires_architectural_spike,
    requires_ui_component,
    requires_worker_slice,
)
from tools.prd_pipeline.prd_manager import PRDManager


def test_decomposer_generates_spikes_and_vertical_slices(temp_project: Path):
    """Verifies automated spike detection and INVEST vertical slice generation."""
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


def test_slice_detection_backward_compatibility_delegates(temp_project: Path):
    """Verifies that private slice detection delegates remain functional on PRDDecomposer."""
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
