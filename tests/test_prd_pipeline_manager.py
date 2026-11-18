"""Tests for PRDManager, buffer audits, and registry synchronization."""

from __future__ import annotations

from pathlib import Path

from tools.prd_pipeline.decomposer import PRDDecomposer
from tools.prd_pipeline.manager import (
    AuditSummary,
    PRDManager,
    PRDRecord,
    PRDScanner,
    PRDStage,
    RequirementAuditor,
)
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


def _write_proposed_task(temp_project: Path, filename: str, scope_body: str) -> None:
    proposed_dir = temp_project / "docs" / "project" / "backlog" / "proposed"
    proposed_dir.mkdir(parents=True, exist_ok=True)
    (proposed_dir / filename).write_text(
        f"# TASK-{filename[:4]}: Example\n\n## Scope of Work\n{scope_body}\n\n"
        "## Definition of Done\n- Done.\n",
        encoding="utf-8",
    )


def _epic_ids(temp_project: Path) -> list[str]:
    mgr = PRDManager(temp_project)
    auditor = RequirementAuditor(temp_project / "docs" / "project" / "backlog")
    return [e["id"] for e in auditor.audit(mgr.load_prds()).epic_proposed_tasks]


def test_scope_rule_flags_task_with_more_than_eight_top_level_items(temp_project: Path):
    """A task with nine top-level scope entries is an epic, even when each entry is small."""
    entries = "\n".join(f"{n}. Entry {n}\n   - detail" for n in range(1, 10))
    _write_proposed_task(temp_project, "9001-many-entries.md", entries)
    assert _epic_ids(temp_project) == ["TASK-9001"]


def test_scope_rule_flags_task_spanning_two_components(temp_project: Path):
    """A task that names two component roots is an epic, even with few entries."""
    body = (
        "1. Route in `services/game_session/src/game_session/routes.py`\n"
        "2. Proxy in `gateway/api/src/gateway_api/routers/games.py`"
    )
    _write_proposed_task(temp_project, "9002-two-components.md", body)
    assert _epic_ids(temp_project) == ["TASK-9002"]


def test_scope_rule_keeps_single_component_task_with_nested_details(temp_project: Path):
    """Nested bullets are details of one entry. They do not make a task an epic."""
    body = "\n".join(
        [
            "1. Route in `services/soundscape/src/soundscape/routers/cue.py`",
            "   - detail one",
            "   - detail two",
            "   - detail three",
            "   - detail four",
            "   - detail five",
            "   - detail six",
            "   - detail seven",
            "2. Test in `tests/test_blackbox_soundscape_cue.py`",
        ]
    )
    _write_proposed_task(temp_project, "9003-nested-details.md", body)
    assert _epic_ids(temp_project) == []


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
