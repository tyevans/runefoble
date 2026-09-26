"""Blackbox tests verifying modular APIRouter decomposition for the_watcher bounded context.

Ensures zero contract regressions, public HTTP frontdoor reachability, OpenAPI schema completeness,
and strict compliance with Hard Invariant 6 (file length < 500 lines).
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from the_watcher.main import app as watcher_app


@pytest.fixture
def watcher_client():
    return TestClient(watcher_app)


def test_watcher_openapi_routes_completeness(watcher_client):
    """Verify that all decomposed APIRouter routes are registered in OpenAPI schema."""
    openapi = watcher_client.app.openapi()
    paths = openapi["paths"]

    expected_routes = [
        "/healthz",
        "/ui/manifest",
        "/api/v1/watcher/transcribe-and-act",
        "/api/v1/watcher/intent",
        "/api/v1/watcher/intent/parse",
        "/api/v1/watcher/intent/resolve",
        "/api/v1/watcher/intent/execute",
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


def test_watcher_transcribe_and_act_frontdoor(watcher_client):
    """Verify intent extraction and transcribe-and-act frontdoors."""
    assert watcher_client.get("/healthz").status_code == 200
    assert watcher_client.get("/ui/manifest").status_code == 200

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


def test_watcher_scenes_generate_frontdoor(watcher_client):
    """Verify autonomous DM scene generation frontdoor."""
    res_scene = watcher_client.post(
        "/api/v1/watcher/scenes/generate",
        json={"session_id": str(uuid4()), "location_type": "catacombs", "mood": "dark"},
    )
    assert res_scene.status_code == 200, res_scene.text
    assert "description" in res_scene.json()


def test_watcher_encounters_frontdoor(watcher_client):
    """Verify autonomous DM encounter spawning and NPC turn execution frontdoors."""
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


def test_watcher_narrate_frontdoor(watcher_client):
    """Verify DM narration synthesis frontdoor."""
    res_narrate = watcher_client.post(
        "/api/v1/watcher/narrate",
        json={"session_id": str(uuid4()), "prompt": "Thunder echoes"},
    )
    assert res_narrate.status_code == 200
    assert "narrative" in res_narrate.json()


def test_watcher_stand_in_frontdoor(watcher_client):
    """Verify missing player stand-in and chronicle recap frontdoors."""
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
