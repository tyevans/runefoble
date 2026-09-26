"""Blackbox TDD tests for character level progression, spell slots, and spellbook preparation.

Governed by Hard Invariant 7: All feature tests interact strictly through public HTTP
frontdoors (POST /api/v1/characters, POST /api/v1/characters/{id}/level-up,
POST /api/v1/characters/{id}/spells/prepare, POST /api/v1/characters/{id}/spells/cast,
GET /api/v1/characters/{id}) with ZERO backdoor internal state tampering.
"""

from character_sheet.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_blackbox_character_level_progression_and_spell_casting():
    """Exercise complete level progression, spell preparation, casting, and slot exhaustion."""
    # a) Create a character via POST /api/v1/characters
    create_payload = {
        "name": "Raistlin Majere",
        "character_class": "Wizard",
        "max_hp": 18,
    }
    create_res = client.post("/api/v1/characters", json=create_payload)
    assert create_res.status_code == 200, create_res.text
    char_data = create_res.json()
    char_id = char_data["character_id"]
    assert char_data["level"] == 1
    assert char_data["max_hp"] == 18
    # Level 1 gets 2 1st-level slots
    slots = {int(k): v for k, v in char_data["spell_slots"].items()}
    assert slots[1] == 2

    # b) Level up from 1 to 3 via POST /api/v1/characters/{id}/level-up
    # Level 1 -> 2
    lvl2_res = client.post(f"/api/v1/characters/{char_id}/level-up")
    assert lvl2_res.status_code == 200, lvl2_res.text
    lvl2_data = lvl2_res.json()
    assert lvl2_data["level"] == 2
    assert lvl2_data["max_hp"] > 18
    hp_at_lvl2 = lvl2_data["max_hp"]
    slots_lvl2 = {int(k): v for k, v in lvl2_data["spell_slots"].items()}
    assert slots_lvl2[1] == 3

    # Level 2 -> 3
    lvl3_res = client.post(f"/api/v1/characters/{char_id}/level-up")
    assert lvl3_res.status_code == 200, lvl3_res.text
    lvl3_data = lvl3_res.json()
    assert lvl3_data["level"] == 3
    assert lvl3_data["max_hp"] > hp_at_lvl2
    slots_lvl3 = {int(k): v for k, v in lvl3_data["spell_slots"].items()}
    # Level 3 gets 4 1st-level and 2 2nd-level slots
    assert slots_lvl3[1] == 4
    assert slots_lvl3[2] == 2

    # c) Prepare spells via POST /api/v1/characters/{id}/spells/prepare
    prep1_res = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Magic Missile", "spell_level": 1},
    )
    assert prep1_res.status_code == 200, prep1_res.text
    prep1_data = prep1_res.json()
    assert "Magic Missile" in prep1_data["prepared_spells"]
    assert "Magic Missile" in prep1_data["spellbook"]

    prep2_res = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Misty Step", "spell_level": 2},
    )
    assert prep2_res.status_code == 200, prep2_res.text
    prep2_data = prep2_res.json()
    assert "Misty Step" in prep2_data["prepared_spells"]
    assert "Misty Step" in prep2_data["spellbook"]

    # d) Cast spell via POST /api/v1/characters/{id}/spells/cast (decrements remaining slot, verifies slot level)
    # Cast Magic Missile (slot level 1)
    cast1_res = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Magic Missile", "slot_level": 1},
    )
    assert cast1_res.status_code == 200, cast1_res.text
    cast1_data = cast1_res.json()
    cast1_slots = {int(k): v for k, v in cast1_data["spell_slots"].items()}
    assert cast1_slots[1] == 3
    assert cast1_slots[2] == 2

    # Cast Misty Step (slot level 2)
    cast2_res = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Misty Step", "slot_level": 2},
    )
    assert cast2_res.status_code == 200, cast2_res.text
    cast2_data = cast2_res.json()
    cast2_slots = {int(k): v for k, v in cast2_data["spell_slots"].items()}
    assert cast2_slots[2] == 1

    # Cast Misty Step again (slot level 2) -> decrements to 0
    cast3_res = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Misty Step", "slot_level": 2},
    )
    assert cast3_res.status_code == 200, cast3_res.text
    cast3_data = cast3_res.json()
    cast3_slots = {int(k): v for k, v in cast3_data["spell_slots"].items()}
    assert cast3_slots[2] == 0

    # e) Attempting to cast when slots are exhausted returns HTTP 400 with detail containing 'INSUFFICIENT_SPELL_SLOTS'
    cast_fail_res = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Misty Step", "slot_level": 2},
    )
    assert cast_fail_res.status_code == 400
    assert "INSUFFICIENT_SPELL_SLOTS" in cast_fail_res.json().get("detail", "")

    # f) Verify GET /api/v1/characters/{id} reflects updated level, max_hp, spellbook, and spell slots.
    get_res = client.get(f"/api/v1/characters/{char_id}")
    assert get_res.status_code == 200, get_res.text
    final_data = get_res.json()
    assert final_data["level"] == 3
    assert final_data["max_hp"] == lvl3_data["max_hp"]
    assert "Magic Missile" in final_data["spellbook"]
    assert "Misty Step" in final_data["spellbook"]
    final_slots = {int(k): v for k, v in final_data["spell_slots"].items()}
    assert final_slots[1] == 3
    assert final_slots[2] == 0


def test_blackbox_spell_slot_inference_and_custom_level_up():
    """Verify default spell level inference when slot_level is omitted and custom hp increase."""
    create_res = client.post(
        "/api/v1/characters",
        json={"name": "Elminster", "character_class": "Wizard", "max_hp": 25},
    )
    assert create_res.status_code == 200
    char_id = create_res.json()["character_id"]

    # Level up with custom hp_increase and target_level
    lvl_res = client.post(
        f"/api/v1/characters/{char_id}/level-up",
        json={"hp_increase": 10, "target_level": 2},
    )
    assert lvl_res.status_code == 200
    data = lvl_res.json()
    assert data["level"] == 2
    assert data["max_hp"] == 35

    # Prepare spell without explicit spell_level (infers level 1 for Magic Missile)
    prep_res = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Magic Missile"},
    )
    assert prep_res.status_code == 200
    assert "Magic Missile" in prep_res.json()["prepared_spells"]

    # Cast spell without explicit slot_level (infers level 1)
    cast_res = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Magic Missile"},
    )
    assert cast_res.status_code == 200
    slots = {int(k): v for k, v in cast_res.json()["spell_slots"].items()}
    assert slots[1] == 2
