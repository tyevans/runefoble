"""Blackbox TDD frontdoor test suite for Campaign Analytics Redis Streams Worker.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 2: DeclarativeAggregate event sourcing
- Hard Invariant 6: File length limit (< 500 lines, target < 200 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

import pytest
from campaign_analytics.storage import CampaignAnalyticsStorage
from campaign_analytics.worker import CampaignAnalyticsWorker
from runefoble_events.events import (
    AbsenteeRecapGenerated,
    CharacterHealthChanged,
    CombatEncounterStarted,
    CombatRoundAdvanced,
    DiceRolled,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    TokenMoved,
    TokenPlaced,
)
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus

S_STR = "runefoble.events.session"
B_STR = "runefoble.events.board"
C_STR = "runefoble.events.character"
W_STR = "runefoble.events.watcher"

WorkerEnv = tuple[CampaignAnalyticsStorage, CampaignAnalyticsWorker, RedisStreamsEventBus]


@pytest.fixture
def env() -> WorkerEnv:
    storage = CampaignAnalyticsStorage()
    mock_redis = MockAsyncRedis()
    cg = RedisConsumerGroup(client=mock_redis)
    worker = CampaignAnalyticsWorker(
        storage=storage,
        consumer_group=cg,
        group_name="test_analytics_workers",
        consumer_name="test_worker_1",
    )
    return storage, worker, RedisStreamsEventBus(client=mock_redis)


def _evt(cls: Any, sid: Any, cid: Any, **kwargs: Any) -> Any:
    return cls(aggregate_id=sid, session_id=sid, campaign_id=cid, **kwargs)


def _hp(
    chid: Any, sid: Any, cid: Any, d: int, curr: int, max_hp: int = 40
) -> CharacterHealthChanged:
    return CharacterHealthChanged(
        aggregate_id=chid,
        session_id=sid,
        campaign_id=cid,
        delta=d,
        current_hp=curr,
        max_hp=max_hp,
        source="test",
    )


@pytest.mark.asyncio
async def test_worker_setup_groups_and_stream_routing(env: WorkerEnv) -> None:
    """Verify consumer group initialization across all 4 streams and message acknowledgment."""
    storage, worker, event_bus = env
    await worker.setup_groups()
    sid, cid = uuid4(), uuid4()

    await event_bus.publish_event(S_STR, _evt(SessionCreated, sid, cid, title="Test"))
    await event_bus.publish_event(
        B_STR, _evt(TokenPlaced, sid, cid, token_id="t1", name="Tok", token_type="pc", x=5, y=5)
    )

    processed = await worker.process_once(count=10)
    assert processed == 2
    assert worker.processed_count == 2
    assert storage.resolve_campaign_id(str(sid)) == str(cid)


@pytest.mark.asyncio
async def test_worker_spatial_and_damage_projection(env: WorkerEnv) -> None:
    """Verify spatial movement, damage, and knockout event ingestion within sub-200ms latency SLA."""
    storage, worker, event_bus = env
    cid, sid, chid = uuid4(), uuid4(), uuid4()
    await worker.setup_groups()

    await event_bus.publish_event(
        B_STR,
        _evt(TokenPlaced, sid, cid, token_id=str(chid), name="V", token_type="pc", x=10, y=15),
    )
    await event_bus.publish_event(
        B_STR,
        _evt(
            TokenMoved,
            sid,
            cid,
            token_id=str(chid),
            name="V",
            from_x=10,
            from_y=15,
            to_x=12,
            to_y=18,
        ),
    )
    await event_bus.publish_event(C_STR, _hp(chid, sid, cid, -25, 15))
    await event_bus.publish_event(C_STR, _hp(chid, sid, cid, -15, 0))

    t0 = time.perf_counter()
    processed = await worker.process_once(count=10)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert processed >= 4
    assert elapsed_ms < 200.0, f"Worker projection took {elapsed_ms}ms, exceeding 200ms SLA"
    assert len(storage.spatial_records) == 5  # placed, moved, damage, damage, knockout
    assert any(r["event_type"] == "knockout" for r in storage.spatial_records)
    assert any(m["milestone_type"] == "character_knockout" for m in storage.milestones)


@pytest.mark.asyncio
async def test_worker_combat_and_dice_lifecycle(env: WorkerEnv) -> None:
    """Verify combat rounds, dice criticals, and damage/healing attribution to combatants."""
    storage, worker, event_bus = env
    cid, sid = uuid4(), uuid4()
    vid, did = uuid4(), uuid4()
    await worker.setup_groups()

    crit_roll = DiceRolled(
        aggregate_id=uuid4(),
        session_id=str(sid),
        roller_id=str(vid),
        roller_name="Valeros",
        formula="1d20+7",
        total=27,
        is_crit=True,
    )
    await event_bus.publish_event(S_STR, _evt(SessionCreated, sid, cid, title="Lair"))
    await event_bus.publish_event(
        S_STR, _evt(CombatEncounterStarted, sid, cid, round_number=1, combatants=[])
    )
    await event_bus.publish_event(W_STR, crit_roll)
    await event_bus.publish_event(
        S_STR, _evt(CombatRoundAdvanced, sid, cid, round_number=1, active_combatant_id=str(vid))
    )
    await event_bus.publish_event(C_STR, _hp(did, sid, cid, -65, 135, max_hp=200))

    await worker.process_once(count=10)

    valeros_stats = storage.combatants.get(f"{cid}:{sid}:{vid}")
    assert valeros_stats is not None
    assert valeros_stats["damage_dealt"] == 65
    assert valeros_stats["critical_hits"] == 1
    assert valeros_stats["turns_taken"] == 1


@pytest.mark.asyncio
async def test_worker_chronicle_milestone_events(env: WorkerEnv) -> None:
    """Verify session lifecycle and absentee recap events create chronicle milestones."""
    storage, worker, event_bus = env
    cid, sid = uuid4(), uuid4()
    await worker.setup_groups()

    recap_event = AbsenteeRecapGenerated(
        aggregate_id=uuid4(),
        session_id=str(sid),
        character_id=str(uuid4()),
        character_name="Merisiel Rogue",
        stand_in_persona="Sneaky Drunkard",
        narrative_summary="Merisiel flanked the sentries.",
        highlights=["Stole key"],
    )
    await event_bus.publish_event(S_STR, _evt(SessionStarted, sid, cid))
    await event_bus.publish_event(W_STR, recap_event)
    await event_bus.publish_event(S_STR, _evt(SessionEnded, sid, cid, summary="Finished"))

    await worker.process_once(count=10)

    m_types = [m["milestone_type"] for m in storage.milestones]
    assert "session_start" in m_types
    assert "recap" in m_types
    assert "session_end" in m_types
