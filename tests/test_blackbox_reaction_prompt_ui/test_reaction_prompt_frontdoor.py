"""Blackbox frontdoor integration tests for reaction prompt API contracts (TASK-0158).

Governed by:
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from runefoble_platform.mock_redis import MockAsyncRedis


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


def test_reaction_prompt_frontdoor_declare_and_resolve(
    client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    """Verify declare reaction pauses turn, feeds prompt component, and resolve resumes turn."""
    session_id, marcus_id, _ = _setup_active_combat(client)

    # 1. Spoken reaction halts turn and returns prompt parameters
    declare_res = client.post(
        f"/api/v1/sessions/{session_id}/reactions/declare",
        json={
            "reacting_combatant_id": marcus_id,
            "reacting_combatant_name": "Marcus",
            "trigger_phrase": "I cast Shield!",
            "reaction_type": "shield",
            "timeout_seconds": 15.0,
            "details": {"spell": "Shield", "ac_bonus": 5},
        },
    )
    assert declare_res.status_code == 200
    prompt_data = declare_res.json()
    assert prompt_data["status"] == "paused"
    assert prompt_data["reaction_type"] == "shield"
    reaction_id = prompt_data["reaction_id"]

    # 2. UI polls active reaction status
    active_res = client.get(f"/api/v1/sessions/{session_id}/reactions/active")
    assert active_res.status_code == 200
    active_data = active_res.json()
    assert active_data["turn_paused_for_reaction"] is True
    assert active_data["active_reaction"]["reaction_id"] == reaction_id

    # 3. User clicks action button in prompt component to resolve
    resolve_res = client.post(
        f"/api/v1/sessions/{session_id}/reactions/{reaction_id}/resolve",
        json={"action_taken": "cast_shield", "details": {"applied_ac": 5}},
    )
    assert resolve_res.status_code == 200
    resolve_data = resolve_res.json()
    assert resolve_data["status"] == "resolved"
    assert resolve_data["resumed"] is True

    # 4. Verify turn resumed
    after_res = client.get(f"/api/v1/sessions/{session_id}/reactions/active")
    assert after_res.status_code == 200
    assert after_res.json()["turn_paused_for_reaction"] is False


def test_ready_action_card_frontdoor_registration(client: TestClient) -> None:
    """Verify ready-action card registration and trigger evaluation via public frontdoor."""
    session_id, marcus_id, _ = _setup_active_combat(client)

    # 1. Register ready-action from card
    reg_res = client.post(
        f"/api/v1/sessions/{session_id}/reactions/ready-action",
        json={
            "combatant_id": marcus_id,
            "combatant_name": "Marcus",
            "trigger_type": "enemy_enters_range",
            "trigger_condition": "if the goblin steps into the hallway",
            "readied_action": "Shoot Heavy Crossbow",
            "range_cells": 6,
        },
    )
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert reg_data["combatant_name"] == "Marcus"
    assert reg_data["readied_action"] == "Shoot Heavy Crossbow"

    # 2. Evaluate triggers on combat event
    eval_res = client.post(
        f"/api/v1/sessions/{session_id}/reactions/evaluate-triggers",
        json={
            "event_type": "TokenMoved",
            "event_data": {"token_id": "token-goblin-1", "range_cells": 4},
        },
    )
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["triggered_count"] >= 1
    assert eval_data["triggered_actions"][0]["readied_action"] == "Shoot Heavy Crossbow"
