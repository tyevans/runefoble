"""Tests for PRDManager, buffer audits, and registry synchronization."""

from __future__ import annotations

from pathlib import Path

from tools.prd_pipeline.decomposer import PRDDecomposer
from tools.prd_pipeline.manager import (
    AuditSummary,
    PRDRecord,
    PRDScanner,
    PRDStage,
    RequirementAuditor,
)
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

    summary = mgr.audit_summary()
    assert isinstance(summary, AuditSummary)
    assert summary.total_prds == 1
    assert prd.canonical_id in summary.undecomposed_prds


def test_prd_scanner_and_models(temp_project: Path):
    """Verifies direct PRDScanner parsing and PRDStage categorization."""
    mgr = PRDManager(temp_project)
    prd = mgr.create_prd(
        title="Fog of War",
        persona="The DM",
        target_bc="board_state",
        summary="Dynamic sight lines.",
        status="Shaped",
    )

    scanner = PRDScanner(temp_project / "docs" / "project" / "product")
    files = scanner.list_files()
    assert prd.file_path in files

    record = scanner.parse_file(prd.file_path)
    assert isinstance(record, PRDRecord)
    assert record.canonical_id == "PRD-0001"
    assert record.title == "Fog of War"
    assert record.target_bc == "board_state"
    assert PRDStage.SHAPED.value == "shaped"


def test_requirement_auditor_detects_epic_tasks(temp_project: Path):
    """Verifies auditor flags oversized proposed tasks failing INVEST small criteria."""
    mgr = PRDManager(temp_project)
    mgr.create_prd(
        title="Epic Quest",
        persona="Hero",
        target_bc="campaign_lore",
        summary="A huge journey.",
        status="Accepted",
    )

    proposed_dir = temp_project / "docs" / "project" / "backlog" / "proposed"
    proposed_dir.mkdir(parents=True, exist_ok=True)
    epic_task = proposed_dir / "9999-epic-lore-microservice.md"
    epic_task.write_text(
        """# TASK-9999: Epic Lore Microservice

## Scope of Work
- Item 1
- Item 2
- Item 3
- Item 4
""",
        encoding="utf-8",
    )

    auditor = RequirementAuditor(temp_project / "docs" / "project" / "backlog")
    summary = auditor.audit(mgr.load_prds())
    assert len(summary.epic_proposed_tasks) >= 1
    assert summary.epic_proposed_tasks[0]["id"] == "TASK-9999"


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
