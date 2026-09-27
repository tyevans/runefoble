"""Blackbox tests verifying spoken reaction interrupts and turn pause/resumption (TASK-0155)."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import deserialize_event


def _setup_active_combat(client: TestClient) -> tuple[str, str, str]:
    """Helper to initialize an active combat encounter with two combatants."""
    campaign_id = str(uuid4())
    create_res = client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Reaction Arena", "dm_id": "the_watcher"},
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]

    marcus_id = str(uuid4())
    client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "player_id": "player_marcus",
            "character_id": marcus_id,
            "character_name": "Marcus",
            "character_class": "Wizard",
        },
    )
    client.post(f"/api/v1/sessions/{session_id}/start")

    goblin_id = "token-goblin-1"
    start_combat = client.post(
        f"/api/v1/sessions/{session_id}/combat/start",
        json={
            "combatants": [
                {"combatant_id": goblin_id, "combatant_name": "Goblin Raider", "is_npc": True},
                {"combatant_id": marcus_id, "combatant_name": "Marcus", "is_npc": False},
            ]
        },
    )
    assert start_combat.status_code == 200
    assert start_combat.json()["in_combat"] is True

    client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={
            "combatant_id": goblin_id,
            "combatant_name": "Goblin Raider",
            "initiative_score": 18,
            "is_npc": True,
        },
    )
    client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={
            "combatant_id": marcus_id,
            "combatant_name": "Marcus",
            "initiative_score": 12,
            "is_npc": False,
        },
    )

    combat_state = client.get(f"/api/v1/sessions/{session_id}/combat").json()
    active_combatant_id = combat_state["combat_active_id"]
    return session_id, marcus_id, active_combatant_id


def test_spoken_reaction_interrupt_pauses_turn(client: TestClient, mock_bus: MockAsyncRedis):
    """AC 1: Shouting recognized reaction phrases halts active turn resolution."""
    session_id, marcus_id, goblin_id = _setup_active_combat(client)

    declare_res = client.post(
        f"/sessions/{session_id}/reactions/declare",
        json={
            "reacting_combatant_id": marcus_id,
            "reacting_combatant_name": "Marcus",
            "trigger_phrase": "I cast Shield!",
            "reaction_type": "shield",
            "timeout_seconds": 15.0,
            "details": {"spell": "Shield", "ac_bonus": 5},
        },
    )
    assert declare_res.status_code == 200, declare_res.text
    data = declare_res.json()
    assert data["status"] == "paused"
    assert data["reaction_type"] == "shield"
    assert data["reacting_combatant_id"] == marcus_id
    assert data["paused_turn_combatant_id"] == goblin_id
    reaction_id = data["reaction_id"]
    assert reaction_id

    # Verify combat.turn.paused_for_reaction CloudEvent in Redis Stream
    stream_events = mock_bus.streams.get("runefoble.events.session", [])
    paused_events = [
        deserialize_event(fields)
        for _, fields in stream_events
        if "paused_for_reaction" in fields.get("event_type", "")
    ]
    assert len(paused_events) >= 1
    pe = paused_events[-1]
    assert pe.reaction_id == reaction_id
    assert pe.reacting_combatant_id == marcus_id
    assert pe.reaction_type == "shield"
    ce_dict = pe.to_cloudevent_dict()
    assert "paused_for_reaction" in ce_dict["type"]

    # Verify active reaction query frontdoor
    active_res = client.get(f"/sessions/{session_id}/reactions/active")
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["turn_paused_for_reaction"] is True
    assert active_data["active_reaction"]["reaction_id"] == reaction_id

    # AC: Resolve the reaction interrupt
    resolve_res = client.post(
        f"/sessions/{session_id}/reactions/{reaction_id}/resolve",
        json={"action_taken": "cast_shield", "details": {"applied_ac": 5}},
    )
    assert resolve_res.status_code == 200
    res_data = resolve_res.json()
    assert res_data["status"] == "resolved"
    assert res_data["resumed"] is True

    # Verify ReactionResolvedEvent in Redis Stream
    stream_events = mock_bus.streams.get("runefoble.events.session", [])
    resolved_events = [
        deserialize_event(fields)
        for _, fields in stream_events
        if "reaction_resolved" in fields.get("event_type", "")
        or "reaction.resolved" in fields.get("event_type", "")
    ]
    assert len(resolved_events) >= 1
    re = resolved_events[-1]
    assert re.reaction_id == reaction_id
    assert re.resumed is True

    # Verify session reflects resumed turn state
    active_res2 = client.get(f"/sessions/{session_id}/reactions/active")
    assert active_res2.status_code == 200
    assert active_res2.json()["turn_paused_for_reaction"] is False
    assert active_res2.json()["active_reaction"] is None


def test_reaction_declare_error_handling(client: TestClient):
    """Test validation and error handling on reaction declarations."""
    # 1. Non-existent session
    bad_uuid = str(uuid4())
    res = client.post(
        f"/sessions/{bad_uuid}/reactions/declare",
        json={"reacting_combatant_id": "c-1", "trigger_phrase": "Shield!"},
    )
    assert res.status_code == 404

    # 2. Declare outside combat
    c_res = client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(uuid4()), "title": "Peaceful Session"},
    )
    session_id = c_res.json()["session_id"]
    res_no_combat = client.post(
        f"/sessions/{session_id}/reactions/declare",
        json={"reacting_combatant_id": "c-1", "trigger_phrase": "Counterspell!"},
    )
    assert res_no_combat.status_code == 400
    assert "not in combat" in res_no_combat.json()["detail"]
