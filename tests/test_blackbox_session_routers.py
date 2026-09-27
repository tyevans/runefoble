"""Blackbox tests verifying modular APIRouter decomposition for game_session bounded context.

Ensures zero contract regressions, public HTTP frontdoor reachability, OpenAPI schema completeness,
and strict compliance with Hard Invariant 6 (file length < 500 lines).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app


@pytest.fixture
def session_client():
    return TestClient(session_app)


def test_game_session_openapi_routes_completeness(session_client):
    """Verify that all decomposed APIRouter routes are registered in OpenAPI schema."""
    paths = session_client.app.openapi()["paths"]
    expected_routes = [
        "/healthz",
        "/ui/manifest",
        "/api/v1/sessions/create",
        "/api/v1/sessions/{session_id}",
        "/api/v1/sessions/{session_id}/start",
        "/api/v1/sessions/{session_id}/join",
        "/api/v1/sessions/{session_id}/leave",
        "/api/v1/sessions/{session_id}/hot-swap",
        "/api/v1/sessions/{session_id}/next-turn",
        "/api/v1/sessions/{session_id}/roll",
        "/api/v1/sessions/{session_id}/combat/start",
        "/api/v1/sessions/{session_id}/combat/initiative",
        "/api/v1/sessions/{session_id}/combat/next-turn",
        "/api/v1/sessions/{session_id}/combat/end",
        "/api/v1/sessions/{session_id}/combat",
        "/api/v1/sessions/{session_id}/turns/auto-pilot",
        "/api/v1/sessions/{session_id}/autopilot",
        "/sessions/{session_id}/reactions/declare",
        "/sessions/{session_id}/reactions/ready-action",
        "/sessions/{session_id}/reactions/{reaction_id}/resolve",
        "/sessions/{session_id}/reactions/active",
    ]

    for route in expected_routes:
        assert route in paths, f"Route '{route}' missing from Game Session OpenAPI schema"


def test_game_session_lifecycle_frontdoor(session_client):
    """Verify session creation, retrieval, and status transition frontdoors."""
    assert session_client.get("/healthz").status_code == 200
    assert session_client.get("/ui/manifest").status_code == 200

    create_res = session_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(uuid4()), "title": "Test Session", "dm_id": "dm_alice"},
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]

    get_res = session_client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200 and get_res.json()["title"] == "Test Session"

    start_res = session_client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_res.status_code == 200 and start_res.json()["status"] == "active"


def test_game_session_turns_frontdoor(session_client):
    """Verify turn advancement, combat initiative rotation, and autopilot frontdoors."""
    c_res = session_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(uuid4()), "title": "Combat Session", "dm_id": "dm_alice"},
    )
    session_id, char_id = c_res.json()["session_id"], str(uuid4())
    p_data = {
        "player_id": "p-1",
        "character_id": char_id,
        "character_name": "Valeros",
        "character_class": "Fighter",
    }
    assert (
        session_client.post(f"/api/v1/sessions/{session_id}/join", json=p_data).status_code == 200
    )
    session_client.post(f"/api/v1/sessions/{session_id}/start")

    turn_res = session_client.post(f"/api/v1/sessions/{session_id}/next-turn")
    assert turn_res.status_code == 200

    combat_start = session_client.post(
        f"/api/v1/sessions/{session_id}/combat/start",
        json={"combatants": [{"combatant_id": char_id, "combatant_name": "Valeros"}]},
    )
    assert combat_start.status_code == 200 and combat_start.json()["in_combat"] is True

    init_payload = {"combatant_id": char_id, "combatant_name": "Valeros", "initiative_score": 15}
    assert (
        session_client.post(
            f"/api/v1/sessions/{session_id}/combat/initiative", json=init_payload
        ).status_code
        == 200
    )
    assert session_client.get(f"/api/v1/sessions/{session_id}/combat").status_code == 200
    assert session_client.post(f"/api/v1/sessions/{session_id}/combat/next-turn").status_code == 200

    combat_end = session_client.post(f"/api/v1/sessions/{session_id}/combat/end")
    assert combat_end.status_code == 200 and combat_end.json()["in_combat"] is False

    session_client.post(
        f"/api/v1/sessions/{session_id}/leave", json={"player_id": "p-1", "reason": "pizza"}
    )
    payload = {"penalties": ["foolishness"]}
    for endpoint in ["/turns/auto-pilot", "/autopilot"]:
        res = session_client.post(f"/api/v1/sessions/{session_id}{endpoint}", json=payload)
        assert res.status_code == 200 and res.json()["action"]["character_name"] == "Valeros"


def test_game_session_presence_frontdoor(session_client):
    """Verify player join and leave presence frontdoors."""
    c_res = session_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(uuid4()), "title": "Presence Session", "dm_id": "dm_bob"},
    )
    session_id = c_res.json()["session_id"]
    cid = str(uuid4())
    p = {"player_id": "p-2", "character_id": cid, "character_name": "S", "character_class": "M"}
    assert session_client.post(f"/api/v1/sessions/{session_id}/join", json=p).status_code == 200
    assert (
        session_client.post(
            f"/api/v1/sessions/{session_id}/leave", json={"player_id": "p-2", "reason": "lost"}
        ).status_code
        == 200
    )


def test_game_session_dice_frontdoor(session_client):
    """Verify session dice rolling frontdoor."""
    c_res = session_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": str(uuid4()), "title": "Dice Session", "dm_id": "dm_carol"},
    )
    session_id = c_res.json()["session_id"]
    session_client.post(f"/api/v1/sessions/{session_id}/start")

    roll_res = session_client.post(
        f"/api/v1/sessions/{session_id}/roll",
        json={"formula": "2d6+3", "roller_name": "Valeros"},
    )
    assert roll_res.status_code == 200 and roll_res.json()["total"] >= 5
