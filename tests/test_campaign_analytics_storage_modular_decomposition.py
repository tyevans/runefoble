"""Tests verifying modular decomposition and line budgets of campaign analytics storage & queries.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from campaign_analytics.queries import (
    calculate_mvp_rankings,
    create_milestone_record,
    create_spatial_record,
    query_campaign_timeline,
    query_spatial_heatmap,
)
from campaign_analytics.storage import CampaignAnalyticsStorage


def test_modular_file_length_limits() -> None:
    """Verify storage facade and query modules strictly respect line length budgets."""
    pkg_dir = (
        Path(__file__).resolve().parent.parent
        / "services"
        / "campaign_analytics"
        / "src"
        / "campaign_analytics"
    )
    storage_file = pkg_dir / "storage.py"
    spatial_file = pkg_dir / "queries" / "spatial.py"
    mvp_file = pkg_dir / "queries" / "mvp.py"
    timeline_file = pkg_dir / "queries" / "timeline.py"

    assert storage_file.exists()
    assert spatial_file.exists()
    assert mvp_file.exists()
    assert timeline_file.exists()

    storage_lines = len(storage_file.read_text().splitlines())
    spatial_lines = len(spatial_file.read_text().splitlines())
    mvp_lines = len(mvp_file.read_text().splitlines())
    timeline_lines = len(timeline_file.read_text().splitlines())

    assert storage_lines < 170, f"storage.py has {storage_lines} lines (exceeds 170 target)"
    assert spatial_lines < 120, f"spatial.py has {spatial_lines} lines (exceeds 120 target)"
    assert mvp_lines < 120, f"mvp.py has {mvp_lines} lines (exceeds 120 target)"
    assert timeline_lines < 110, f"timeline.py has {timeline_lines} lines (exceeds 110 target)"


def test_direct_query_spatial_heatmap() -> None:
    """Verify query_spatial_heatmap standalone aggregation."""
    cid, sid = str(uuid4()), str(uuid4())
    records = [
        create_spatial_record(cid, sid, "t1", "Valeros", 10, 10, "movement"),
        create_spatial_record(cid, sid, "t1", "Valeros", 12, 14, "damage", damage=15),
    ]
    resp = query_spatial_heatmap(records, campaign_id=cid, cell_size=5)
    assert resp.total_points == 2
    assert len(resp.cells) == 1
    assert resp.cells[0].damage_total == 15


def test_direct_calculate_mvp_rankings() -> None:
    """Verify calculate_mvp_rankings standalone computation."""
    cid, sid = str(uuid4()), str(uuid4())
    combatants = {
        "p1": {
            "campaign_id": cid,
            "session_id": sid,
            "combatant_id": "p1",
            "combatant_name": "Valeros",
            "damage_dealt": 50,
            "damage_taken": 10,
            "healing_provided": 0,
            "critical_hits": 2,
            "fumbles": 0,
            "turns_taken": 2,
        },
        "p2": {
            "campaign_id": cid,
            "session_id": sid,
            "combatant_id": "p2",
            "combatant_name": "Kyra",
            "damage_dealt": 0,
            "damage_taken": 5,
            "healing_provided": 40,
            "critical_hits": 0,
            "fumbles": 0,
            "turns_taken": 2,
        },
    }
    resp = calculate_mvp_rankings(combatants, campaign_id=cid)
    assert resp.overall_mvp is not None
    assert resp.overall_mvp.recipient_id == "p1"
    award_titles = [a.title for a in resp.awards]
    assert "Most Lethal" in award_titles
    assert "Guardian Angel" in award_titles


def test_direct_query_campaign_timeline() -> None:
    """Verify query_campaign_timeline standalone filtering and ordering."""
    cid, sid = str(uuid4()), str(uuid4())
    rec1, _ = create_milestone_record(
        cid, sid, "start", "Session 1", "Start", "2026-09-01T10:00:00Z"
    )
    rec2, _ = create_milestone_record(
        cid, sid, "end", "Session 1 End", "End", "2026-09-01T14:00:00Z"
    )
    resp = query_campaign_timeline([rec2, rec1], campaign_id=cid, limit=1)
    assert resp.total_milestones == 2
    assert len(resp.milestones) == 1
    assert resp.milestones[0].type == "start"


@pytest.mark.asyncio
async def test_storage_facade_delegation_integrity() -> None:
    """Verify CampaignAnalyticsStorage correctly delegates to modular query implementations."""
    storage = CampaignAnalyticsStorage()
    cid, sid = str(uuid4()), str(uuid4())

    await storage.record_spatial_position(cid, sid, "tok-1", "Hero", 5, 5, "movement")
    await storage.record_combatant_stat(cid, sid, "enc-1", "hero-1", "Hero", damage_dealt=100)
    await storage.record_milestone(cid, sid, "discovery", "Secret Found", "A hidden door")

    h = await storage.get_campaign_heatmaps(cid)
    assert h.total_points == 1

    mvp = await storage.get_campaign_mvp(cid)
    assert mvp.overall_mvp is not None
    assert mvp.overall_mvp.recipient_name == "Hero"

    t = await storage.get_campaign_timeline(cid)
    assert t.total_milestones == 1
    assert t.milestones[0].title == "Secret Found"
