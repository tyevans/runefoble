"""Tests for modular Game Session projections (InitiativeProjection, PresenceProjection, and re-exports)."""

from uuid import uuid4

from game_session.projections import (
    CombatantInitiativeModel,
    InitiativeProjection,
    InitiativeReadModel,
    ParticipantPresenceModel,
    PresenceProjection,
    PresenceReadModel,
    SessionReadProjection,
    TokenReadModel,
)
from runefoble_events.events import (
    CharacterControlTransferred,
    CombatEncounterEnded,
    CombatEncounterStarted,
    InitiativeRolled,
    InitiativeTurnAdvanced,
    PlayerJoinedSession,
    PlayerLeftSession,
)
from runefoble_platform.event_deserializer import deserialize_event


def test_projections_reexports() -> None:
    """Verify that game_session.projections cleanly re-exports all required models and classes."""
    assert InitiativeProjection is not None
    assert PresenceProjection is not None
    assert SessionReadProjection is not None
    assert InitiativeReadModel is not None
    assert CombatantInitiativeModel is not None
    assert PresenceReadModel is not None
    assert ParticipantPresenceModel is not None
    assert TokenReadModel is not None


def test_initiative_projection_lifecycle() -> None:
    """Test InitiativeProjection with combat start, multiple rolls, turn advancement, and end."""
    proj = InitiativeProjection()
    sess_id = uuid4()
    str_id = str(sess_id)

    # 1. Start combat
    proj.apply_event(CombatEncounterStarted(aggregate_id=sess_id, round_number=1))
    init_state = proj.get_initiative(sess_id)
    assert init_state is not None
    assert init_state.in_combat is True
    assert init_state.combat_round == 1
    assert init_state.combat_active_id is None

    # 2. Roll initiatives: Valeros rolls 12 (PC), Kyra rolls 18 (PC), Goblin rolls 18 (NPC)
    valeros_id = str(uuid4())
    kyra_id = str(uuid4())
    goblin_id = "goblin-1"

    proj.apply_event(
        InitiativeRolled(
            aggregate_id=sess_id,
            combatant_id=valeros_id,
            combatant_name="Valeros",
            initiative_score=12,
            is_npc=False,
        )
    )
    proj.apply_event(
        InitiativeRolled(
            aggregate_id=sess_id,
            combatant_id=kyra_id,
            combatant_name="Kyra",
            initiative_score=18,
            is_npc=False,
        )
    )
    proj.apply_event(
        InitiativeRolled(
            aggregate_id=sess_id,
            combatant_id=goblin_id,
            combatant_name="Goblin",
            initiative_score=18,
            is_npc=True,
        )
    )

    # In tie-break: same score 18, PC takes priority over NPC (1 if not is_npc else 0)
    order = proj.get_initiative_order(sess_id)
    assert len(order) == 3
    assert order[0].combatant_id == kyra_id
    assert order[1].combatant_id == goblin_id
    assert order[2].combatant_id == valeros_id

    # 3. Advance turn
    proj.apply_event(
        InitiativeTurnAdvanced(
            aggregate_id=sess_id,
            round_number=1,
            active_combatant_id=kyra_id,
            turn_seconds_remaining=45,
        )
    )
    active = proj.get_active_combatant(sess_id)
    assert active is not None
    assert active.combatant_name == "Kyra"
    assert proj.get_initiative(str_id).turn_seconds_remaining == 45

    # 4. Dict event handling
    proj.apply_event(
        {
            "session_id": str_id,
            "event_type": "InitiativeTurnAdvanced",
            "round_number": 2,
            "active_combatant_id": valeros_id,
            "turn_seconds_remaining": 60,
        }
    )
    assert proj.get_initiative(str_id).combat_round == 2
    assert proj.get_active_combatant(str_id).combatant_name == "Valeros"

    # 5. End combat
    proj.apply_event(CombatEncounterEnded(aggregate_id=sess_id, total_rounds=2))
    assert proj.get_initiative(str_id).in_combat is False
    assert proj.get_initiative(str_id).combat_active_id is None


def test_presence_projection_lifecycle() -> None:
    """Test PresenceProjection with participant joins, leaves, hot-swaps, and presence queries."""
    proj = PresenceProjection()
    sess_id = uuid4()
    str_id = str(sess_id)
    char_id = uuid4()

    # 1. Player joins
    proj.apply_event(
        PlayerJoinedSession(
            aggregate_id=sess_id,
            player_id="player-1",
            character_id=char_id,
            character_name="Fighter Bob",
            character_class="Fighter",
        )
    )
    assert proj.is_player_present(sess_id, "player-1") is True
    assert "player-1" in proj.get_present_players(str_id)
    part = proj.get_participants(sess_id)["player-1"]
    assert part.character_name == "Fighter Bob"
    assert part.is_stand_in_active is False

    # 2. Player leaves (disconnect / stand-in activated)
    proj.apply_event(
        PlayerLeftSession(
            aggregate_id=sess_id,
            player_id="player-1",
            reason="network disconnect",
        )
    )
    assert proj.is_player_present(sess_id, "player-1") is False
    assert part.is_stand_in_active is True
    assert "player-1" not in proj.get_present_players(str_id)

    # 3. Hot-swap control transfer back to player
    new_char_id = uuid4()
    proj.apply_event(
        CharacterControlTransferred(
            session_id=sess_id,
            aggregate_id=sess_id,
            player_id="player-1",
            character_id=new_char_id,
        )
    )
    assert proj.is_player_present(sess_id, "player-1") is True
    assert proj.get_participants(sess_id)["player-1"].is_stand_in_active is False
    assert proj.get_participants(sess_id)["player-1"].character_id == str(new_char_id)

    # 4. Dict event handling
    proj.apply_event(
        {
            "session_id": str_id,
            "event_type": "PlayerJoinedSession",
            "player_id": "player-2",
            "character_id": str(uuid4()),
            "character_name": "Wizard Alice",
            "character_class": "Wizard",
        }
    )
    assert proj.is_player_present(sess_id, "player-2") is True
    assert len(proj.get_present_players(str_id)) == 2


def test_event_deserializer_trace_and_dict() -> None:
    """Test deserialize_event with trace headers and fallback types."""
    # Plain dict
    fields = {"event_type": "CustomUnknownEvent", "data": "value"}
    res = deserialize_event(fields)
    assert res == fields

    # W3C trace headers preservation
    fields_with_trace = {
        "event_type": "CustomUnknownEvent",
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "tracestate": "rojo=1",
        "data": "xyz",
    }
    res_trace = deserialize_event(fields_with_trace)
    assert res_trace["traceparent"] == fields_with_trace["traceparent"]
    assert res_trace["tracestate"] == "rojo=1"
