"""Tests for PRDManager, buffer audits, and registry synchronization."""

from __future__ import annotations

from pathlib import Path

from tools.prd_pipeline.decomposer import PRDDecomposer
from tools.prd_pipeline.prd_manager import PRDManager
from tools.prd_pipeline.registry_sync import RegistrySynchronizer
from tools.prd_pipeline.writer import PlanWriter


def test_prd_manager_lifecycle_and_creation(temp_project: Path):
    """Verifies PRD creation, auto-increment numbering, and file placement."""
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
    """Verifies backlog buffer health checks and undecomposed PRD detection."""
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


def test_registry_synchronizer_repairs_stale_links_and_indexes(temp_project: Path):
    """Verifies registry reconciliation and PRIORITY.md task indexing."""
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

    sync = RegistrySynchronizer(temp_project)
    res = sync.sync_all()

    assert res["prds_synced"] == 1
    assert res["tasks_synced"] >= len(plan.all_tasks)

    priority_content = (temp_project / "docs" / "project" / "backlog" / "PRIORITY.md").read_text(
        encoding="utf-8"
    )
    for t in plan.all_tasks:
        assert t.canonical_id in priority_content
