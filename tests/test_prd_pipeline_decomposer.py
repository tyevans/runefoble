"""Tests for PRDDecomposer execution, PlanWriter persistence, and task templating."""

from __future__ import annotations

from pathlib import Path

from tools.prd_pipeline.decomposer import PRDDecomposer
from tools.prd_pipeline.models import SliceType
from tools.prd_pipeline.prd_manager import PRDManager
from tools.prd_pipeline.templates import (
    create_user_story_draft,
    format_task_markdown,
    format_user_story_markdown,
    render_acceptance_criteria,
    serialize_yaml_list,
)
from tools.prd_pipeline.writer import PlanWriter


def test_plan_writer_persists_tasks_and_stories(temp_project: Path):
    """Verifies that PlanWriter correctly persists task and user story markdown files."""
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


def test_decomposer_task_draft_delegates(temp_project: Path):
    """Verifies that private draft factory helper delegates remain functional on PRDDecomposer."""
    mgr = PRDManager(temp_project)
    prd = mgr.create_prd(
        title="Interactive Canvas",
        persona="Player",
        target_bc="board_state",
        summary="Canvas UI component.",
        status="Accepted",
    )
    decomposer = PRDDecomposer(temp_project)

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
