"""Blackbox TDD frontdoor test suite for Campaign Analytics Storage Engine & Aggregations.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 6: File length limit (< 500 lines, target < 180 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from campaign_analytics.storage import CampaignAnalyticsStorage


@pytest.fixture
def storage() -> CampaignAnalyticsStorage:
    return CampaignAnalyticsStorage()


def test_storage_session_mapping_and_resolution(storage: CampaignAnalyticsStorage) -> None:
    """Verify session-to-campaign mapping, resolution, and campaign matching logic."""
    sid, cid = str(uuid4()), str(uuid4())
    assert storage.resolve_campaign_id(sid) == sid

    storage.map_session(sid, cid)
    assert storage.resolve_campaign_id(sid) == cid
    assert storage._matches_campaign(cid, sid, cid) is True
    assert storage._matches_campaign(cid, sid, sid) is True
    assert storage._matches_campaign("other-c", "other-s", cid) is False


@pytest.mark.asyncio
async def test_storage_spatial_heatmap_aggregations(storage: CampaignAnalyticsStorage) -> None:
    """Verify spatial coordinate bucketing, density accumulation, and metric filtering."""
    cid, sid = str(uuid4()), str(uuid4())
    storage.map_session(sid, cid)

    # Record movement, damage, and knockout
    await storage.record_spatial(cid, sid, "t1", "Valeros", 12, 18, "movement")
    await storage.record_spatial(cid, sid, "t1", "Valeros", 14, 19, "damage", damage=30)
    await storage.record_spatial(cid, sid, "t1", "Valeros", 14, 19, "knockout")

    # cell_size=5: (12, 18) and (14, 19) bucket into cell (10, 15)
    h5 = await storage.get_heatmap(campaign_id=cid, cell_size=5, metric="all")
    assert h5.total_points == 3
    assert len(h5.cells) == 1
    c5 = h5.cells[0]
    assert (c5.x, c5.y) == (10, 15)
    assert c5.movement_count == 1
    assert c5.damage_total == 30
    assert c5.hit_count == 1
    assert c5.knockout_count == 1
    # density = movement(1) + damage(30//5=6) + knockout(5) = 12
    assert c5.density == 12
    assert h5.max_density == 12

    # cell_size=10: bucketed into (10, 10)
    h10 = await storage.get_heatmap(campaign_id=cid, cell_size=10, metric="all")
    assert h10.cells[0].x == 10 and h10.cells[0].y == 10

    # Metric filter: movement only
    hm_mov = await storage.get_heatmap(campaign_id=cid, metric="movement")
    assert hm_mov.total_points == 1
    assert hm_mov.cells[0].movement_count == 1
    assert hm_mov.cells[0].damage_total == 0

    # Metric filter: damage only
    hm_dmg = await storage.get_heatmap(campaign_id=cid, metric="damage")
    assert hm_dmg.total_points == 2
    assert hm_dmg.cells[0].damage_total == 30


@pytest.mark.asyncio
async def test_storage_combatant_stats_and_mvp_calculations(
    storage: CampaignAnalyticsStorage,
) -> None:
    """Verify cumulative combatant statistics, scoring formula, and MVP awards."""
    cid, sid, eid = str(uuid4()), str(uuid4()), "enc-lair"
    p1, p2 = str(uuid4()), str(uuid4())

    # P1: 65 damage, 1 crit, 1 turn
    await storage.record_combatant_stat(
        cid, sid, eid, p1, "Valeros", damage_dealt=40, critical_hits=1, turns_taken=1
    )
    # Cumulative update for P1: +25 damage dealt
    await storage.record_combatant_stat(cid, sid, eid, p1, "Valeros", damage_dealt=25)

    # P2: 45 healing, 1 turn
    await storage.record_combatant_stat(
        cid, sid, eid, p2, "Kyra", healing_provided=45, turns_taken=1
    )

    mvp = await storage.get_mvp(campaign_id=cid, session_id=sid, encounter_id=eid)
    assert mvp.overall_mvp is not None
    # P1 score: 65*1.0 + 1*10.0 + 1*2.0 = 77.0. P2 score: 45*1.5 + 1*2.0 = 69.5
    assert mvp.overall_mvp.recipient_id == p1
    assert mvp.overall_mvp.score == 77.0

    awards = {a.title: a for a in mvp.awards}
    assert awards["Most Lethal"].recipient_id == p1
    assert awards["Most Lethal"].score == 65
    assert awards["Guardian Angel"].recipient_id == p2
    assert awards["Guardian Angel"].score == 45
    assert awards["Nat 20 Master"].recipient_id == p1

    # Filter with non-existent encounter returns no awards
    empty_mvp = await storage.get_mvp(campaign_id=cid, encounter_id="non-existent")
    assert empty_mvp.overall_mvp is None
    assert len(empty_mvp.awards) == 0


@pytest.mark.asyncio
async def test_storage_milestones_and_timeline_ordering(storage: CampaignAnalyticsStorage) -> None:
    """Verify chronological timeline ordering, limit slicing, and metadata storage."""
    cid, sid = str(uuid4()), str(uuid4())

    await storage.record_milestone(
        cid, sid, "session_start", "Start", "Began", "2026-09-01T10:00:00Z"
    )
    await storage.record_milestone(
        cid,
        sid,
        "boss_encounter",
        "Boss Spawned",
        "Dragon appears",
        "2026-09-01T11:00:00Z",
        {"cr": 14},
    )
    await storage.record_milestone(
        cid, sid, "session_end", "End", "Finished", "2026-09-01T12:00:00Z"
    )

    timeline = await storage.get_timeline(campaign_id=cid, limit=2)
    assert timeline.total_milestones == 3
    assert len(timeline.milestones) == 2
    assert timeline.milestones[0].type == "session_start"
    assert timeline.milestones[1].type == "boss_encounter"
    assert timeline.milestones[1].metadata == {"cr": 14}


@pytest.mark.asyncio
async def test_storage_backward_compatible_aliases(storage: CampaignAnalyticsStorage) -> None:
    """Verify 100% backward compatibility for all public method aliases."""
    cid, sid = str(uuid4()), str(uuid4())
    await storage.record_spatial_position(cid, sid, "t1", "Valeros", 10, 15, "damage", damage=20)
    await storage.record_combatant_stat(cid, sid, "enc1", "p1", "Valeros", damage_dealt=50)
    await storage.record_milestone(cid, sid, "quest_complete", "Trophy", "Won battle")

    heatmaps = await storage.get_campaign_heatmaps(campaign_id=cid)
    assert heatmaps.total_points == 1
    assert heatmaps.cells[0].damage_total == 20

    mvp = await storage.get_campaign_mvp(campaign_id=cid)
    assert mvp.overall_mvp is not None
    assert mvp.overall_mvp.recipient_id == "p1"

    timeline = await storage.get_campaign_timeline(campaign_id=cid)
    assert timeline.total_milestones == 1
    assert timeline.milestones[0].title == "Trophy"
