"""Unit tests for CampaignChronicleAggregate and event sourcing.

Governed by:
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 2: Domain state changes flow strictly through DeclarativeAggregate subclasses.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from campaign_analytics.aggregate import CampaignChronicleAggregate
from runefoble_events.analytics import (
    ChronicleMilestoneRecorded,
    CombatTelemetrySnapshotCreated,
    EncounterMvpAwarded,
)
from runefoble_platform.event_sourcing import AggregateRepository, InMemoryEventStore


def test_campaign_chronicle_aggregate_event_sourcing() -> None:
    """Verify CampaignChronicleAggregate creates, handles, and tracks uncommitted domain events."""
    agg = CampaignChronicleAggregate(aggregate_id=uuid4())
    agg.record_milestone(
        campaign_id="camp-agg-1",
        session_id="sess-agg-1",
        milestone_type="boss_defeat",
        title="Slain the Hydra",
        description="The party cut off all seven heads.",
        metadata={"xp_reward": 5000},
    )
    agg.award_mvp(
        campaign_id="camp-agg-1",
        session_id="sess-agg-1",
        encounter_id="enc-hydra",
        combatant_id="char-barbarian",
        combatant_name="Amiri",
        award_title="Hydra Bane",
        metric_name="damage_dealt",
        score=150.0,
    )
    agg.record_snapshot(
        campaign_id="camp-agg-1",
        session_id="sess-agg-1",
        total_damage=250,
        total_movements=45,
        active_combatants=5,
    )

    events = list(agg.uncommitted_events)
    assert len(events) == 3
    assert isinstance(events[0], ChronicleMilestoneRecorded)
    assert isinstance(events[1], EncounterMvpAwarded)
    assert isinstance(events[2], CombatTelemetrySnapshotCreated)

    assert len(agg.state.milestones) == 1
    assert agg.state.milestones[0].title == "Slain the Hydra"
    assert len(agg.state.mvp_awards) == 1
    assert agg.state.mvp_awards[0].award_title == "Hydra Bane"
    assert agg.state.total_damage_logged == 250
    assert agg.state.total_movements_logged == 45


@pytest.mark.asyncio
async def test_campaign_chronicle_aggregate_repository_roundtrip() -> None:
    """Verify storing and reconstituting CampaignChronicleAggregate from event store."""
    store = InMemoryEventStore()
    repo = AggregateRepository(event_store=store, aggregate_factory=CampaignChronicleAggregate)

    agg_id = uuid4()
    agg = CampaignChronicleAggregate(aggregate_id=agg_id)
    agg.record_milestone(
        campaign_id="camp-persist-1",
        session_id="sess-persist-1",
        milestone_type="quest_complete",
        title="Artifact Recovered",
        description="Found the Sunblade in Castle Ravenloft.",
    )
    agg.award_mvp(
        campaign_id="camp-persist-1",
        session_id="sess-persist-1",
        encounter_id="enc-strahd",
        combatant_id="char-cleric",
        combatant_name="Kyra",
        award_title="Beacon of Light",
        metric_name="healing_provided",
        score=85.0,
    )
    await repo.save(agg)

    reconstituted = await repo.load(agg_id)
    assert reconstituted is not None
    assert reconstituted.state.campaign_id == "camp-persist-1"
    assert len(reconstituted.state.milestones) == 1
    assert reconstituted.state.milestones[0].title == "Artifact Recovered"
    assert len(reconstituted.state.mvp_awards) == 1
    assert reconstituted.state.mvp_awards[0].award_title == "Beacon of Light"
