"""Blackbox TDD tests for live multi-user turn order, initiative tracker & timer.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All setup and verification are performed strictly through public HTTP API endpoints
using TestClient(app) from game_session.main.
"""

from uuid import UUID, uuid4

import pytest
from eventsource.domain.stream_id import StreamId
from fastapi.testclient import TestClient
from game_session.main import app
from runefoble_events.events import (
    CombatEncounterEnded,
    CombatEncounterStarted,
    InitiativeRolled,
    InitiativeTurnAdvanced,
)
from runefoble_platform.event_sourcing import get_event_store


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_blackbox_combat_initiative_encounter_lifecycle_and_turn_cycling(client: TestClient):
    """End-to-end blackbox test: start combat, roll initiatives, cycle turns across rounds, and end combat."""
    campaign_id = str(uuid4())

    # 1. Frontdoor session setup: Create session
    create_resp = client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Ambush at Red Larch", "dm_id": "the_watcher"},
    )
    assert create_resp.status_code == 200, create_resp.text
    session_data = create_resp.json()
    session_id = session_data["session_id"]

    # 2. Join players via public API
    valeros_id = str(uuid4())
    kyra_id = str(uuid4())
    client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "player_id": "player-1",
            "character_id": valeros_id,
            "character_name": "Valeros",
            "character_class": "Fighter",
        },
    )
    client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "player_id": "player-2",
            "character_id": kyra_id,
            "character_name": "Kyra",
            "character_class": "Cleric",
        },
    )

    # 3. Start session
    start_session_resp = client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_session_resp.status_code == 200

    # 4. Start combat encounter via POST /api/v1/sessions/{session_id}/combat/start
    combat_start_resp = client.post(f"/api/v1/sessions/{session_id}/combat/start")
    assert combat_start_resp.status_code == 200, combat_start_resp.text
    combat_state = combat_start_resp.json()
    assert combat_state["in_combat"] is True
    assert combat_state["combat_round"] == 1
    assert combat_state["initiative_order"] == []
    assert combat_state["combat_active_id"] is None

    # 5. Submit initiative rolls via POST /api/v1/sessions/{session_id}/combat/initiative
    # Kyra rolls 12
    roll1_resp = client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={
            "combatant_id": kyra_id,
            "combatant_name": "Kyra",
            "initiative_score": 12,
            "is_npc": False,
        },
    )
    assert roll1_resp.status_code == 200
    assert roll1_resp.json()["combat_active_id"] == kyra_id
    assert len(roll1_resp.json()["initiative_order"]) == 1

    # Goblin Archer (NPC) rolls 15
    goblin_id = "npc-goblin-archer-1"
    roll2_resp = client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={
            "combatant_id": goblin_id,
            "combatant_name": "Goblin Archer",
            "initiative_score": 15,
            "is_npc": True,
        },
    )
    assert roll2_resp.status_code == 200

    # Valeros rolls 20 (Natural 20!)
    roll3_resp = client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={
            "combatant_id": valeros_id,
            "combatant_name": "Valeros",
            "initiative_score": 20,
            "is_npc": False,
        },
    )
    assert roll3_resp.status_code == 200

    # 6. Verify public GET /api/v1/sessions/{session_id}/combat projection
    combat_query_resp = client.get(f"/api/v1/sessions/{session_id}/combat")
    assert combat_query_resp.status_code == 200
    state = combat_query_resp.json()
    assert state["in_combat"] is True
    assert state["combat_round"] == 1
    # Check deterministic sorted descending order: Valeros (20) -> Goblin (15) -> Kyra (12)
    order = state["initiative_order"]
    assert len(order) == 3
    assert [c["combatant_id"] for c in order] == [valeros_id, goblin_id, kyra_id]
    assert [c["initiative_score"] for c in order] == [20, 15, 12]

    # 7. Advance Turn 1 (Valeros -> Goblin Archer)
    next_turn_1 = client.post(
        f"/api/v1/sessions/{session_id}/combat/next-turn",
        json={"turn_seconds": 45},
    )
    assert next_turn_1.status_code == 200
    t1_state = next_turn_1.json()
    assert t1_state["combat_active_id"] == goblin_id
    assert t1_state["combat_round"] == 1
    assert t1_state["turn_seconds_remaining"] == 45

    # 8. Advance Turn 2 (Goblin Archer -> Kyra)
    next_turn_2 = client.post(
        f"/api/v1/sessions/{session_id}/combat/next-turn",
        json={"turn_seconds": 60},
    )
    assert next_turn_2.status_code == 200
    t2_state = next_turn_2.json()
    assert t2_state["combat_active_id"] == kyra_id
    assert t2_state["combat_round"] == 1

    # 9. Advance Turn 3 (Kyra -> loops back to round 2, Valeros)
    next_turn_3 = client.post(f"/api/v1/sessions/{session_id}/combat/next-turn")
    assert next_turn_3.status_code == 200
    t3_state = next_turn_3.json()
    assert t3_state["combat_active_id"] == valeros_id
    assert t3_state["combat_round"] == 2

    # 10. Mid-combat initiative arrival (Reinforcement: Bugbear Chieftain rolls 18)
    bugbear_id = "npc-bugbear-boss"
    roll_mid = client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={
            "combatant_id": bugbear_id,
            "combatant_name": "Bugbear Chieftain",
            "initiative_score": 18,
            "is_npc": True,
        },
    )
    assert roll_mid.status_code == 200
    mid_order = roll_mid.json()["initiative_order"]
    assert len(mid_order) == 4
    # Order should now be: Valeros (20), Bugbear (18), Goblin (15), Kyra (12)
    assert [c["combatant_id"] for c in mid_order] == [valeros_id, bugbear_id, goblin_id, kyra_id]

    # Advance to Bugbear's turn in round 2
    next_turn_4 = client.post(f"/api/v1/sessions/{session_id}/combat/next-turn")
    assert next_turn_4.status_code == 200
    assert next_turn_4.json()["combat_active_id"] == bugbear_id
    assert next_turn_4.json()["combat_round"] == 2

    # 11. End combat encounter via POST /api/v1/sessions/{session_id}/combat/end
    end_resp = client.post(f"/api/v1/sessions/{session_id}/combat/end")
    assert end_resp.status_code == 200, end_resp.text
    end_state = end_resp.json()
    assert end_state["in_combat"] is False
    assert end_state["combat_active_id"] is None

    # Observable GET verifies combat has concluded
    concluded_resp = client.get(f"/api/v1/sessions/{session_id}/combat")
    assert concluded_resp.status_code == 200
    assert concluded_resp.json()["in_combat"] is False

    # 12. Verify event stream persistence of combat events
    store = get_event_store()
    stream_id = StreamId(UUID(session_id), "GameSession")
    envelopes = [env async for env in store.read_stream(stream_id)]
    event_types = [type(env.event) for env in envelopes]
    assert CombatEncounterStarted in event_types
    assert InitiativeRolled in event_types
    assert InitiativeTurnAdvanced in event_types
    assert CombatEncounterEnded in event_types


def test_blackbox_start_combat_with_initial_combatants_and_tiebreaking(client: TestClient):
    """Verify starting combat with pre-defined combatants and PC vs NPC tie-breaking."""
    campaign_id = str(uuid4())
    create_resp = client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Dragon Lair", "dm_id": "the_watcher"},
    )
    session_id = create_resp.json()["session_id"]

    # Start combat directly with initial combatants, testing tiebreaking
    # PC and NPC both rolled 14. PC (Ezren) must come before NPC (Orc Warrior).
    initial_combatants = [
        {
            "combatant_id": "npc-orc-1",
            "combatant_name": "Orc Warrior",
            "initiative_score": 14,
            "is_npc": True,
        },
        {
            "combatant_id": "pc-ezren",
            "combatant_name": "Ezren",
            "initiative_score": 14,
            "is_npc": False,
        },
        {
            "combatant_id": "pc-merisiel",
            "combatant_name": "Merisiel",
            "initiative_score": 22,
            "is_npc": False,
        },
    ]

    start_resp = client.post(
        f"/api/v1/sessions/{session_id}/combat/start",
        json={"combatants": initial_combatants},
    )
    assert start_resp.status_code == 200
    state = start_resp.json()
    assert state["in_combat"] is True
    assert state["combat_round"] == 1
    # Merisiel (22) -> Ezren (14, PC) -> Orc Warrior (14, NPC)
    order = state["initiative_order"]
    assert [c["combatant_id"] for c in order] == ["pc-merisiel", "pc-ezren", "npc-orc-1"]
    assert state["combat_active_id"] == "pc-merisiel"


def test_blackbox_combat_error_frontdoor_validation(client: TestClient):
    """Verify proper 400 / 404 HTTP errors on invalid combat actions."""
    campaign_id = str(uuid4())
    create_resp = client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": campaign_id, "title": "Peaceful Tavern", "dm_id": "the_watcher"},
    )
    session_id = create_resp.json()["session_id"]

    # 1. Roll initiative before starting combat -> 400 Bad Request
    roll_err = client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={
            "combatant_id": "char-1",
            "combatant_name": "Hero",
            "initiative_score": 10,
            "is_npc": False,
        },
    )
    assert roll_err.status_code == 400
    assert "not in combat" in roll_err.json()["detail"].lower()

    # 2. Advance turn before starting combat -> 400 Bad Request
    next_err = client.post(f"/api/v1/sessions/{session_id}/combat/next-turn")
    assert next_err.status_code == 400
    assert "not in combat" in next_err.json()["detail"].lower()

    # 3. End combat when not in combat -> 400 Bad Request
    end_err = client.post(f"/api/v1/sessions/{session_id}/combat/end")
    assert end_err.status_code == 400
    assert "not in combat" in end_err.json()["detail"].lower()

    # 4. Actions on non-existent session -> 404 Not Found
    non_existent_id = str(uuid4())
    get_err = client.get(f"/api/v1/sessions/{non_existent_id}/combat")
    assert get_err.status_code == 404
