"""Blackbox tests verifying ready-action conditional registry and trigger evaluation (TASK-0155)."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from runefoble_platform.mock_redis import MockAsyncRedis
from runefoble_platform.redis_bus import deserialize_event


def _setup_active_combat(client: TestClient) -> tuple[str, str, str]:
    """Helper to initialize an active combat encounter."""
    campaign_id = str(uuid4())
    create_res = client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Ambush Corridor", "dm_id": "the_watcher"},
    )
    session_id = create_res.json()["session_id"]
    marcus_id = str(uuid4())
    client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "player_id": "p_marcus",
            "character_id": marcus_id,
            "character_name": "Marcus",
            "character_class": "Ranger",
        },
    )
    client.post(f"/api/v1/sessions/{session_id}/start")

    goblin_id = "token-goblin-hallway"
    client.post(
        f"/api/v1/sessions/{session_id}/combat/start",
        json={
            "combatants": [
                {"combatant_id": marcus_id, "combatant_name": "Marcus"},
                {"combatant_id": goblin_id, "combatant_name": "Goblin"},
            ]
        },
    )
    client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={"combatant_id": marcus_id, "combatant_name": "Marcus", "initiative_score": 15},
    )
    client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={"combatant_id": goblin_id, "combatant_name": "Goblin", "initiative_score": 10},
    )
    client.post(f"/api/v1/sessions/{session_id}/combat/next-turn")
    return session_id, marcus_id, goblin_id


def test_ready_action_registration_and_triggering(client: TestClient, mock_bus: MockAsyncRedis):
    """AC 2 & AC 3: Register ready action and execute automatically when condition is met."""
    session_id, marcus_id, goblin_id = _setup_active_combat(client)

    # 1. Register ready-action trigger:
    # "I ready my crossbow to shoot if the goblin steps into the hallway"
    reg_res = client.post(
        f"/sessions/{session_id}/reactions/ready-action",
        json={
            "combatant_id": marcus_id,
            "combatant_name": "Marcus",
            "trigger_type": "enemy_enters_range",
            "trigger_condition": "if the goblin steps into the hallway",
            "readied_action": "shoot crossbow",
            "target_id": goblin_id,
            "range_cells": 6,
        },
    )
    assert reg_res.status_code == 200, reg_res.text
    reg_data = reg_res.json()
    ready_action_id = reg_data["ready_action_id"]
    assert reg_data["status"] == "registered"
    assert reg_data["readied_action"] == "shoot crossbow"

    # Verify ReadyActionRegisteredEvent in Redis Stream
    stream_events = mock_bus.streams.get("runefoble.events.session", [])
    reg_events = [
        deserialize_event(fields)
        for _, fields in stream_events
        if "ready_action_registered" in fields.get("event_type", "")
        or "ready_action.registered" in fields.get("event_type", "")
    ]
    assert len(reg_events) >= 1
    re = reg_events[-1]
    assert re.ready_action_id == ready_action_id
    assert re.combatant_id == marcus_id

    # Verify ready action listed in active query
    active_res = client.get(f"/sessions/{session_id}/reactions/active")
    assert active_res.status_code == 200
    ready_actions = active_res.json()["ready_actions"]
    assert any(a["ready_action_id"] == ready_action_id for a in ready_actions)

    # 2. Goblin moves into the corridor (trigger event)
    eval_res = client.post(
        f"/sessions/{session_id}/reactions/evaluate-triggers",
        json={
            "event_type": "TokenMoved",
            "event_data": {
                "token_id": goblin_id,
                "name": "Goblin",
                "from_x": 2,
                "from_y": 5,
                "to_x": 4,
                "to_y": 5,
            },
        },
    )
    assert eval_res.status_code == 200, eval_res.text
    eval_data = eval_res.json()
    assert eval_data["triggered_count"] == 1
    assert eval_data["triggered_actions"][0]["ready_action_id"] == ready_action_id
    assert eval_data["triggered_actions"][0]["readied_action"] == "shoot crossbow"

    # Verify ReadyActionTriggeredEvent in Redis Stream
    stream_events = mock_bus.streams.get("runefoble.events.session", [])
    trig_events = [
        deserialize_event(fields)
        for _, fields in stream_events
        if "ready_action_triggered" in fields.get("event_type", "")
        or "ready_action.triggered" in fields.get("event_type", "")
    ]
    assert len(trig_events) >= 1
    te = trig_events[-1]
    assert te.ready_action_id == ready_action_id
    assert te.triggering_entity_id == goblin_id

    # Verify ready action is consumed
    active_after = client.get(f"/sessions/{session_id}/reactions/active").json()
    assert not any(a["ready_action_id"] == ready_action_id for a in active_after["ready_actions"])
