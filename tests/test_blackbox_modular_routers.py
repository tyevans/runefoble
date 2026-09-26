"""Blackbox tests verifying modular APIRouter decomposition for the_watcher and game_session.

Ensures zero contract regressions, public HTTP frontdoor reachability, OpenAPI schema completeness,
and strict compliance with Hard Invariant 6 (file length < 500 lines).
"""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from the_watcher.main import app as watcher_app


@pytest.fixture
def watcher_client():
    return TestClient(watcher_app)


@pytest.fixture
def session_client():
    return TestClient(session_app)


def test_watcher_openapi_routes_completeness(watcher_client):
    """Verify that all decomposed APIRouter routes are registered in OpenAPI schema."""
    openapi = watcher_client.app.openapi()
    paths = openapi["paths"]

    expected_routes = [
        "/healthz",
        "/ui/manifest",
        "/api/v1/watcher/transcribe-and-act",
        "/api/v1/watcher/intent",
        "/api/v1/watcher/scenes/generate",
        "/api/v1/watcher/encounters/spawn",
        "/api/v1/watcher/encounters/npc-turn",
        "/api/v1/watcher/narrate",
        "/api/v1/watcher/stand-in/act",
        "/api/v1/watcher/stand-in/recap",
        "/api/v1/watcher/chronicle/recap",
    ]

    for route in expected_routes:
        assert route in paths, f"Route '{route}' missing from The Watcher OpenAPI schema"


def test_game_session_openapi_routes_completeness(session_client):
    """Verify that all decomposed APIRouter routes are registered in OpenAPI schema."""
    openapi = session_client.app.openapi()
    paths = openapi["paths"]

    expected_routes = [
        "/healthz",
        "/ui/manifest",
        "/api/v1/sessions/create",
        "/api/v1/sessions/{session_id}",
        "/api/v1/sessions/{session_id}/start",
        "/api/v1/sessions/{session_id}/join",
        "/api/v1/sessions/{session_id}/leave",
        "/api/v1/sessions/{session_id}/next-turn",
        "/api/v1/sessions/{session_id}/roll",
        "/api/v1/sessions/{session_id}/combat/start",
        "/api/v1/sessions/{session_id}/combat/initiative",
        "/api/v1/sessions/{session_id}/combat/next-turn",
        "/api/v1/sessions/{session_id}/combat/end",
        "/api/v1/sessions/{session_id}/combat",
        "/api/v1/sessions/{session_id}/turns/auto-pilot",
        "/api/v1/sessions/{session_id}/autopilot",
    ]

    for route in expected_routes:
        assert route in paths, f"Route '{route}' missing from Game Session OpenAPI schema"


def test_watcher_frontdoor_endpoints(watcher_client):
    """Verify all Watcher sub-routers respond correctly through public HTTP frontdoors."""
    # 1. Health & manifest
    assert watcher_client.get("/healthz").status_code == 200
    assert watcher_client.get("/ui/manifest").status_code == 200

    # 2. Intent router (/api/v1/watcher/transcribe-and-act and /api/v1/watcher/intent)
    speech_payload = {
        "speaker_id": "p-1",
        "speaker_name": "Thorin",
        "transcript": "I attack the goblin",
        "session_id": str(uuid4()),
        "campaign_id": str(uuid4()),
    }
    res_transcribe = watcher_client.post("/api/v1/watcher/transcribe-and-act", json=speech_payload)
    assert res_transcribe.status_code == 200
    assert res_transcribe.json()["action_type"] == "attack"

    res_intent = watcher_client.post("/api/v1/watcher/intent", json=speech_payload)
    assert res_intent.status_code == 200
    assert res_intent.json()["action_type"] == "attack"

    # 3. Autonomous DM router
    res_scene = watcher_client.post(
        "/api/v1/watcher/scenes/generate",
        json={"session_id": str(uuid4()), "location_type": "catacombs", "mood": "dark"},
    )
    assert res_scene.status_code == 200, res_scene.text
    assert "description" in res_scene.json()

    res_encounter = watcher_client.post(
        "/api/v1/watcher/encounters/spawn",
        json={"session_id": str(uuid4()), "party_level": 2, "party_size": 3},
    )
    assert res_encounter.status_code == 200
    assert "monsters" in res_encounter.json()

    res_npc = watcher_client.post(
        "/api/v1/watcher/encounters/npc-turn",
        json={
            "session_id": str(uuid4()),
            "encounter_id": str(uuid4()),
            "actor_name": "Goblin Skulker",
            "targets": [{"name": "Thorin", "hp": 20}],
            "round_number": 1,
        },
    )
    assert res_npc.status_code == 200
    assert res_npc.json()["actor_name"] == "Goblin Skulker"

    res_narrate = watcher_client.post(
        "/api/v1/watcher/narrate",
        json={"session_id": str(uuid4()), "prompt": "Thunder echoes"},
    )
    assert res_narrate.status_code == 200
    assert "narrative" in res_narrate.json()

    # 4. Stand-in router
    res_stand_in = watcher_client.post(
        "/api/v1/watcher/stand-in/act",
        json={
            "character_name": "Elidor",
            "character_class": "Rogue",
            "penalties": ["drunk"],
            "scene_context": "ambush",
        },
    )
    assert res_stand_in.status_code == 200
    assert res_stand_in.json()["character_name"] == "Elidor"

    res_stand_in_recap = watcher_client.post(
        "/api/v1/watcher/stand-in/recap",
        json={
            "character_name": "Elidor",
            "actions": [{"action_type": "stumble"}],
            "penalties": ["drunk"],
        },
    )
    assert res_stand_in_recap.status_code == 200
    assert "recap" in res_stand_in_recap.json()

    # 5. Chronicle router
    res_chronicle = watcher_client.post(
        "/api/v1/watcher/chronicle/recap",
        json={
            "session_id": str(uuid4()),
            "character_id": str(uuid4()),
            "character_name": "Elidor",
            "actions": [],
        },
    )
    assert res_chronicle.status_code == 200
    assert res_chronicle.json()["character_name"] == "Elidor"


def test_game_session_frontdoor_endpoints(session_client):
    """Verify all Game Session sub-routers respond correctly through public HTTP frontdoors."""
    # 1. Health & manifest
    assert session_client.get("/healthz").status_code == 200
    assert session_client.get("/ui/manifest").status_code == 200

    # 2. Session lifecycle router
    camp_id = str(uuid4())
    create_res = session_client.post(
        "/api/v1/sessions/create",
        json={"campaign_id": camp_id, "title": "Test Session", "dm_id": "dm_alice"},
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["session_id"]

    get_res = session_client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Test Session"

    # Join player
    char_id = str(uuid4())
    join_res = session_client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "player_id": "p-1",
            "character_id": char_id,
            "character_name": "Valeros",
            "character_class": "Fighter",
        },
    )
    assert join_res.status_code == 200

    # Start session
    start_res = session_client.post(f"/api/v1/sessions/{session_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "active"

    # Roll dice
    roll_res = session_client.post(
        f"/api/v1/sessions/{session_id}/roll",
        json={"formula": "2d6+3", "roller_name": "Valeros"},
    )
    assert roll_res.status_code == 200
    assert roll_res.json()["total"] >= 5

    # Advance turn
    turn_res = session_client.post(f"/api/v1/sessions/{session_id}/next-turn")
    assert turn_res.status_code == 200

    # 3. Combat router
    combat_start = session_client.post(
        f"/api/v1/sessions/{session_id}/combat/start",
        json={"combatants": [{"combatant_id": char_id, "combatant_name": "Valeros"}]},
    )
    assert combat_start.status_code == 200, combat_start.text

    assert combat_start.json()["in_combat"] is True

    combat_init = session_client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={
            "combatant_id": char_id,
            "combatant_name": "Valeros",
            "initiative_score": 15,
        },
    )
    assert combat_init.status_code == 200

    combat_state = session_client.get(f"/api/v1/sessions/{session_id}/combat")
    assert combat_state.status_code == 200

    combat_next = session_client.post(f"/api/v1/sessions/{session_id}/combat/next-turn")
    assert combat_next.status_code == 200

    combat_end = session_client.post(f"/api/v1/sessions/{session_id}/combat/end")
    assert combat_end.status_code == 200
    assert combat_end.json()["in_combat"] is False

    # 4. Autopilot router
    # Mark player absent
    leave_res = session_client.post(
        f"/api/v1/sessions/{session_id}/leave",
        json={"player_id": "p-1", "reason": "went to get pizza"},
    )
    assert leave_res.status_code == 200

    autopilot_res = session_client.post(
        f"/api/v1/sessions/{session_id}/turns/auto-pilot",
        json={"penalties": ["foolishness"]},
    )
    assert autopilot_res.status_code == 200
    assert autopilot_res.json()["action"]["character_name"] == "Valeros"

    # Alias /autopilot route
    autopilot_alias_res = session_client.post(
        f"/api/v1/sessions/{session_id}/autopilot",
        json={"penalties": ["foolishness"]},
    )
    assert autopilot_alias_res.status_code == 200
    assert autopilot_alias_res.json()["action"]["character_name"] == "Valeros"


def test_source_files_line_length_limits():
    """Verify Hard Invariant 6: source files must strictly not exceed 500 lines,

    and all newly refactored router modules and entrypoints must be < 250 lines.
    """
    targets = [
        "services/the_watcher/src/the_watcher/main.py",
        "services/the_watcher/src/the_watcher/dependencies.py",
        "services/the_watcher/src/the_watcher/models.py",
        "services/the_watcher/src/the_watcher/routers/intent.py",
        "services/the_watcher/src/the_watcher/routers/autonomous_dm.py",
        "services/the_watcher/src/the_watcher/routers/stand_in.py",
        "services/the_watcher/src/the_watcher/routers/chronicle.py",
        "services/game_session/src/game_session/main.py",
        "services/game_session/src/game_session/dependencies.py",
        "services/game_session/src/game_session/models.py",
        "services/game_session/src/game_session/routers/session.py",
        "services/game_session/src/game_session/routers/combat.py",
        "services/game_session/src/game_session/routers/autopilot.py",
    ]

    for path_str in targets:
        path = Path(path_str)
        assert path.exists(), f"Expected file {path_str} does not exist"
        lines = len(path.read_text().splitlines())
        assert lines < 250, (
            f"File {path_str} has {lines} lines, exceeding the 250 line modular refactor limit"
        )

    # Verify all Python files across both services are < 500 lines
    for bc in ["the_watcher", "game_session"]:
        for py_file in Path(f"services/{bc}").rglob("*.py"):
            lines = len(py_file.read_text().splitlines())
            assert lines < 500, (
                f"File {py_file} has {lines} lines, violating Hard Invariant 6 (< 500 lines)"
            )
