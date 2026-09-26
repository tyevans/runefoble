"""Direct tests for Autonomous DM decomposed domain submodules (TASK-0062).

Verifies:
1. the_watcher.presets: SCENE_PRESETS and build_scene_atmosphere.
2. the_watcher.encounters: build_encounter threat balancing and scaling.
3. the_watcher.tactics: adjudicate_npc_turn tactical decision heuristics.
4. the_watcher.autonomous_dm: re-exports and facade orchestration.
"""

from runefoble_events.events import (
    AutonomousActionResolved,
    EncounterSpawned,
    SceneAtmosphereSet,
)
from the_watcher.autonomous_dm import (
    AutonomousDMEngine,
    adjudicate_npc_turn,
    build_encounter,
    build_scene_atmosphere,
)
from the_watcher.encounters import build_encounter as direct_build_encounter
from the_watcher.presets import SCENE_PRESETS
from the_watcher.presets import build_scene_atmosphere as direct_build_scene
from the_watcher.tactics import adjudicate_npc_turn as direct_adjudicate_turn


def test_presets_submodule_catalog_and_atmosphere():
    """presets.py provides cataloged presets and constructs SceneAtmosphereSet."""
    assert "dungeon" in SCENE_PRESETS
    assert "crypt" in SCENE_PRESETS
    assert "tavern" in SCENE_PRESETS
    assert "forest" in SCENE_PRESETS
    assert "dragon_lair" in SCENE_PRESETS

    scene = direct_build_scene(
        session_id="sess-sub-1",
        location_type="dragon_lair",
        mood="deadly",
    )
    assert isinstance(scene, SceneAtmosphereSet)
    assert scene.location_name == "Scorched Crag of the Wyrm"
    assert "magma" in scene.lighting
    assert "stalactites" in scene.description


def test_encounters_submodule_generation_and_party_scaling():
    """encounters.py balances encounters and scales with party size."""
    # Standard 4-player party, tier 1 medium
    enc_med = direct_build_encounter(
        session_id="sess-sub-2",
        scene_id="sc-sub-2",
        party_level=3,
        party_size=4,
        difficulty="medium",
    )
    assert isinstance(enc_med, EncounterSpawned)
    assert enc_med.threat_level == "medium"
    assert len(enc_med.monsters) == 3

    # Scaled party of 6, adds minion
    enc_scaled = direct_build_encounter(
        session_id="sess-sub-2",
        scene_id="sc-sub-2",
        party_level=3,
        party_size=6,
        difficulty="medium",
    )
    assert len(enc_scaled.monsters) == 4
    assert any(m["role"] == "minion" for m in enc_scaled.monsters)


def test_tactics_submodule_melee_and_finishing_heuristics():
    """tactics.py executes finishing blows on wounded targets and standard strikes in later rounds."""
    # Round 2 standard melee against healthy target
    action_melee = direct_adjudicate_turn(
        session_id="sess-sub-3",
        encounter_id="enc-sub-3",
        actor_name="Orc Marauder",
        targets=[{"name": "Valeros", "hp": 40, "current_hp": 30}],
        round_number=2,
    )
    assert isinstance(action_melee, AutonomousActionResolved)
    assert action_melee.action_type == "melee_strike"
    assert action_melee.hp_impact == -7

    # Finishing strike against target with <= 10 HP
    action_finish = direct_adjudicate_turn(
        session_id="sess-sub-3",
        encounter_id="enc-sub-3",
        actor_name="Orc Marauder",
        targets=[{"name": "Valeros", "hp": 40, "current_hp": 9}],
        round_number=2,
    )
    assert action_finish.action_type == "execute_strike"
    assert action_finish.hp_impact == -10


def test_facade_re_exports_and_class_attributes():
    """autonomous_dm facade correctly re-exports submodules and maintains class compatibility."""
    assert AutonomousDMEngine.SCENE_PRESETS is SCENE_PRESETS
    assert build_scene_atmosphere is direct_build_scene
    assert build_encounter is direct_build_encounter
    assert adjudicate_npc_turn is direct_adjudicate_turn

    engine = AutonomousDMEngine()
    scene = engine.set_scene("sess-facade", location_type="forest", mood="eerie")
    assert scene.location_name == "Whispering Pines of Eldermoor"

    enc = engine.spawn_encounter("sess-facade", scene_id=scene.scene_id, party_level=1)
    assert enc.threat_level == "medium"

    action = engine.resolve_npc_turn(
        "sess-facade",
        encounter_id=enc.encounter_id,
        actor_name="Lich Priest",
        targets=[{"name": "Seoni", "hp": 18}],
    )
    assert action.action_type == "cast_spell"
