"""Blackbox TDD test suite for Watcher Domain Events Modular Decomposition (TASK-0182).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0007: Domain-Driven Design Architecture
- Hard Invariant 6: File length limit (< 80 lines for facade, < 150 lines for submodules)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

from runefoble_events.watcher_events import (
    actions as actions_mod,
)
from runefoble_events.watcher_events import (
    combat as combat_mod,
)
from runefoble_events.watcher_events import (
    factions as factions_mod,
)
from runefoble_events.watcher_events import (
    narrative as narrative_mod,
)
from runefoble_platform.consumer_group import deserialize_event


def test_dice_rolled_properties():
    """Verify DiceRolled exposes its notation and individual rolls."""
    roll = combat_mod.DiceRolled(
        session_id=str(uuid4()),
        roller_id="player-1",
        roller_name="Aria",
        formula="2d6+3",
        total=11,
        rolls=[5, 3],
        is_crit=False,
    )
    assert roll.dice_notation == "2d6+3"
    assert roll.individual_rolls == [5, 3]


def test_event_cloudevent_and_serialization_roundtrip():
    """Verify serialization, deserialization, and CloudEvent compliance for decomposed events."""
    session_id = str(uuid4())

    events_to_test = [
        narrative_mod.PlayerSpokeEvent(
            aggregate_id=uuid4(),
            speaker_id="p-1",
            speaker_name="Aria",
            transcript="I inspect the altar",
        ),
        narrative_mod.WatcherNarrationGenerated(
            aggregate_id=uuid4(),
            narrative_text="A cold draft chills the chamber.",
            tone="eerie",
        ),
        combat_mod.DiceRolled(
            session_id=session_id,
            roller_id="p-1",
            roller_name="Aria",
            formula="1d20+5",
            total=18,
            rolls=[13],
        ),
        actions_mod.WatcherActionProposed(
            action_id="act-1",
            session_id=session_id,
            actor_name="The Watcher",
            action_type="spawn_monster",
            description="Spawn shadowy phantom",
        ),
        factions_mod.FactionCreated(
            campaign_id="camp-1",
            faction_id="fac-iron-hand",
            name="Iron Hand Guild",
        ),
        factions_mod.WorldTickExecuted(
            campaign_id="camp-1",
            tick_number=3,
            intelligence_bulletin="Tensions rise between guilds.",
        ),
    ]

    for event in events_to_test:
        # 1. CloudEvent dictionary conversion
        ce_dict = event.to_cloudevent_dict()
        assert ce_dict["specversion"] == "1.0"
        assert "data" in ce_dict
        assert ce_dict["id"] == str(event.event_id)

        # 2. Redis Bus serialization & deserialization roundtrip
        message_fields = {
            "event_type": event.event_type,
            "payload": event.model_dump_json(),
        }
        deserialized = deserialize_event(message_fields)
        assert (
            isinstance(deserialized, type(event))
            or event.__class__.__name__ == type(deserialized).__name__
        )
        assert deserialized.event_id == event.event_id
