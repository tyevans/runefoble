"""Tests for Autonomous DM Session & Scene Orchestration Engine (TASK-0013).

Verifies:
1. Scene generation across presets (dungeon, crypt, tavern, forest, dragon_lair) and arbitrary locations.
2. Encounter generation and balancing across levels and difficulty tiers (easy, medium, hard, deadly).
3. Tactical NPC turn decision trees (targeting lowest HP, spellcasting, finishing strike, charge).
4. CloudEvents 1.0 compliance and EventRegistry registration.
5. FastAPI TestClient endpoints for scenes/generate, encounters/spawn, and encounters/npc-turn.
"""

import pytest
from eventsource.domain.event_registry import default_registry
from fastapi.testclient import TestClient
from runefoble_events.events import (
    AutonomousActionResolved,
    EncounterSpawned,
    SceneAtmosphereSet,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from the_watcher.autonomous_dm import AutonomousDMEngine
from the_watcher.main import app as watcher_app
from the_watcher.main import set_event_bus


@pytest.fixture
def dm_engine() -> AutonomousDMEngine:
    return AutonomousDMEngine()


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(watcher_app)


# ---------------------------------------------------------------------------
# 1. Scene Generation Tests
# ---------------------------------------------------------------------------


def test_scene_generation_dungeon_preset(dm_engine: AutonomousDMEngine):
    """Preset 'dungeon' produces thematic description, lighting, and audio prompt."""
    scene = dm_engine.set_scene("sess-101", location_type="dungeon", mood="suspenseful")
    assert isinstance(scene, SceneAtmosphereSet)
    assert scene.session_id == "sess-101"
    assert scene.scene_id.startswith("scene-")
    assert scene.location_name == "Forgotten Underhalls"
    assert "torches" in scene.lighting
    assert scene.mood == "suspenseful"
    assert "drip" in scene.description
    assert "dungeon ambiance" in scene.ambient_audio_prompt


def test_scene_generation_crypt_and_tavern(dm_engine: AutonomousDMEngine):
    """Presets 'crypt' and 'tavern' set expected location details."""
    crypt = dm_engine.set_scene("sess-102", location_type="crypt", mood="eerie")
    assert crypt.location_name == "Crypt of the Restless Kings"
    assert "moss" in crypt.lighting
    assert "whispers" in crypt.description

    tavern = dm_engine.set_scene("sess-103", location_type="tavern", mood="cozy")
    assert tavern.location_name == "The Wayward Drake Inn"
    assert "hearth" in tavern.lighting
    assert "bard" in tavern.description


def test_scene_generation_arbitrary_fallback(dm_engine: AutonomousDMEngine):
    """Custom uncataloged location generates dynamic atmospheric fallback."""
    scene = dm_engine.set_scene("sess-104", location_type="astral_rift", mood="chaotic")
    assert "Astral Rift Environs" in scene.location_name
    assert "chaotic" in scene.lighting
    assert "astral rift" in scene.ambient_audio_prompt.lower()


# ---------------------------------------------------------------------------
# 2. Encounter Generation & Balancing Tests
# ---------------------------------------------------------------------------


def test_encounter_generation_tier1_easy(dm_engine: AutonomousDMEngine):
    """Tier 1 easy encounter spawns goblin scouts with clear tactical objective."""
    enc = dm_engine.spawn_encounter("sess-201", scene_id="sc-1", party_level=2, difficulty="easy")
    assert isinstance(enc, EncounterSpawned)
    assert enc.session_id == "sess-201"
    assert enc.threat_level == "easy"
    assert "Goblin Scout Ambush" in enc.encounter_name
    assert len(enc.monsters) >= 2
    assert "disperse" in enc.tactical_objective.lower()
    for mon in enc.monsters:
        assert "hp" in mon and "ac" in mon and "cr" in mon
        assert "position" in mon


def test_encounter_generation_tier1_medium(dm_engine: AutonomousDMEngine):
    """Tier 1 medium encounter includes boss and shaman."""
    enc = dm_engine.spawn_encounter("sess-202", scene_id="sc-2", party_level=3, difficulty="medium")
    assert enc.threat_level == "medium"
    names = [m["name"] for m in enc.monsters]
    assert "Goblin Boss" in names
    assert "Goblin Shaman" in names


def test_encounter_generation_tier1_deadly_and_scaling(dm_engine: AutonomousDMEngine):
    """Deadly encounter spawns high-threat monsters; large party receives reinforcements."""
    enc = dm_engine.spawn_encounter("sess-203", scene_id="sc-3", party_level=4, party_size=5, difficulty="deadly")
    assert enc.threat_level == "deadly"
    assert any(m["cr"] == "5" for m in enc.monsters)
    # Party size 5 triggers extra reinforcement minion
    assert any(m["role"] == "minion" for m in enc.monsters)


def test_encounter_generation_tier2_dragon(dm_engine: AutonomousDMEngine):
    """Tier 2 (level 5+) spawns Young Red Dragon encounter."""
    enc = dm_engine.spawn_encounter("sess-204", scene_id="sc-4", party_level=8, difficulty="hard")
    assert any("Dragon" in m["name"] for m in enc.monsters)
    assert "fire breath" in enc.tactical_objective.lower()


# ---------------------------------------------------------------------------
# 3. NPC Turn Tactical Decision Tests
# ---------------------------------------------------------------------------


def test_npc_turn_targets_lowest_hp(dm_engine: AutonomousDMEngine):
    """NPC turn prioritizes target with lowest current HP."""
    targets = [
        {"name": "Valeros", "hp": 30, "current_hp": 25},
        {"name": "Merisiel", "hp": 24, "current_hp": 8},
        {"name": "Kyra", "hp": 28, "current_hp": 19},
    ]
    action = dm_engine.resolve_npc_turn(
        session_id="sess-301",
        encounter_id="enc-1",
        actor_name="Orc Berserker",
        targets=targets,
        round_number=2,
    )
    assert isinstance(action, AutonomousActionResolved)
    assert action.target_name == "Merisiel"
    assert action.action_type == "execute_strike"
    assert action.hp_impact == -10
    assert "Merisiel" in action.narrative


def test_npc_turn_spellcaster_tactics(dm_engine: AutonomousDMEngine):
    """Spellcaster actor casts spell regardless of target HP."""
    targets = [{"name": "Valeros", "hp": 35, "current_hp": 35}]
    action = dm_engine.resolve_npc_turn(
        session_id="sess-302",
        encounter_id="enc-2",
        actor_name="Goblin Shaman",
        targets=targets,
        round_number=1,
    )
    assert action.action_type == "cast_spell"
    assert action.hp_impact == -8
    assert "incantations" in action.narrative


def test_npc_turn_round_one_charge(dm_engine: AutonomousDMEngine):
    """Non-caster in round 1 executes charge attack."""
    targets = [{"name": "Valeros", "hp": 30, "current_hp": 30}]
    action = dm_engine.resolve_npc_turn(
        session_id="sess-303",
        encounter_id="enc-3",
        actor_name="Bugbear Chieftain",
        targets=targets,
        round_number=1,
    )
    assert action.action_type == "charge_attack"
    assert action.hp_impact == -6
    assert "charge" in action.narrative


def test_npc_turn_empty_targets(dm_engine: AutonomousDMEngine):
    """Empty target list yields search action with zero damage."""
    action = dm_engine.resolve_npc_turn(
        session_id="sess-304",
        encounter_id="enc-4",
        actor_name="Goblin Scout",
        targets=[],
        round_number=1,
    )
    assert action.action_type == "search"
    assert action.hp_impact == 0


# ---------------------------------------------------------------------------
# 4. CloudEvents Compliance & Event Registration
# ---------------------------------------------------------------------------


def test_cloudevents_compliance(dm_engine: AutonomousDMEngine):
    """Domain events must conform to CloudEvents 1.0 JSON format."""
    scene = dm_engine.set_scene("sess-ce", location_type="crypt", mood="suspenseful")
    ce_scene = scene.to_cloudevent_dict()
    assert ce_scene["specversion"] == "1.0"
    assert ce_scene["type"] == "runefoble.events.scene.atmosphere_set"
    assert "/runefoble/scene/" in ce_scene["source"]
    assert ce_scene["data"]["location_name"] == "Crypt of the Restless Kings"

    enc = dm_engine.spawn_encounter("sess-ce", scene_id=scene.scene_id)
    ce_enc = enc.to_cloudevent_dict()
    assert ce_enc["specversion"] == "1.0"
    assert ce_enc["type"] == "runefoble.events.encounter.spawned"
    assert "/runefoble/encounter/" in ce_enc["source"]

    action = dm_engine.resolve_npc_turn("sess-ce", encounter_id=enc.encounter_id, actor_name="Ghoul", targets=[{"name": "Kyra", "hp": 15}])
    ce_action = action.to_cloudevent_dict()
    assert ce_action["specversion"] == "1.0"
    assert ce_action["type"] == "runefoble.events.encounter.action_resolved"


def test_events_registered_in_default_registry():
    """Events must be registered in default_registry with their exact event types."""
    assert default_registry.get("runefoble.events.scene.atmosphere_set") is SceneAtmosphereSet
    assert default_registry.get("runefoble.events.encounter.spawned") is EncounterSpawned
    assert default_registry.get("runefoble.events.encounter.action_resolved") is AutonomousActionResolved


# ---------------------------------------------------------------------------
# 5. FastAPI Endpoints Integration Tests
# ---------------------------------------------------------------------------


def test_api_generate_scene(test_client: TestClient):
    """POST /api/v1/watcher/scenes/generate returns SceneAtmosphereSet."""
    mock_bus = RedisStreamsEventBus(client=MockAsyncRedis())
    set_event_bus(mock_bus)

    res = test_client.post(
        "/api/v1/watcher/scenes/generate",
        json={"session_id": "sess-api-1", "location_type": "dungeon", "mood": "suspenseful"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["session_id"] == "sess-api-1"
    assert data["location_name"] == "Forgotten Underhalls"
    assert "torches" in data["lighting"]
    assert "drip" in data["description"]


def test_api_spawn_encounter(test_client: TestClient):
    """POST /api/v1/watcher/encounters/spawn returns EncounterSpawned."""
    mock_bus = RedisStreamsEventBus(client=MockAsyncRedis())
    set_event_bus(mock_bus)

    res = test_client.post(
        "/api/v1/watcher/encounters/spawn",
        json={"session_id": "sess-api-2", "scene_id": "sc-9", "party_level": 3, "party_size": 4, "difficulty": "medium"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["session_id"] == "sess-api-2"
    assert data["threat_level"] == "medium"
    assert len(data["monsters"]) >= 2


def test_api_execute_npc_turn(test_client: TestClient):
    """POST /api/v1/watcher/encounters/npc-turn returns AutonomousActionResolved."""
    mock_bus = RedisStreamsEventBus(client=MockAsyncRedis())
    set_event_bus(mock_bus)

    res = test_client.post(
        "/api/v1/watcher/encounters/npc-turn",
        json={
            "session_id": "sess-api-3",
            "encounter_id": "enc-9",
            "actor_name": "Goblin Shaman",
            "targets": [{"name": "Ezren", "hp": 20, "current_hp": 12}],
            "round_number": 1,
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["session_id"] == "sess-api-3"
    assert data["actor_name"] == "Goblin Shaman"
    assert data["action_type"] == "cast_spell"
    assert data["target_name"] == "Ezren"
    assert data["hp_impact"] == -8
