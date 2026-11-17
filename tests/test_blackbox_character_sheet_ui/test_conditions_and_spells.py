"""Blackbox TDD tests for conditions, DM penalties, spell preparation, and slots.

Governed by ADR-0003, ADR-0004, ADR-0007, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_conditions_and_penalties_lifecycle(client: TestClient, created_character_id: str) -> None:
    """Verify applying conditions, absentee penalties, and removals via frontdoor REST."""
    char_id = created_character_id
    cond_resp = client.post(
        f"/api/v1/characters/{char_id}/conditions",
        json={"condition": "blinded", "duration_rounds": 3, "source": "tactical"},
    )
    assert cond_resp.status_code == 200
    assert "blinded" in cond_resp.json()["conditions"]

    pen_resp = client.post(
        f"/api/v1/characters/{char_id}/penalties",
        json={
            "penalty_type": "drunk",
            "description": "Absentee stand-in penalty",
            "imposed_by": "the_watcher",
        },
    )
    assert pen_resp.status_code == 200
    assert "drunk" in pen_resp.json()["penalties"]

    del_resp = client.delete(f"/api/v1/characters/{char_id}/conditions/blinded")
    assert del_resp.status_code == 200
    assert "blinded" not in del_resp.json()["conditions"]

    del_pen = client.delete(f"/api/v1/characters/{char_id}/penalties/drunk")
    assert del_pen.status_code == 200
    assert "drunk" not in del_pen.json()["penalties"]


def test_spell_slots_and_preparation(client: TestClient, created_character_id: str) -> None:
    """Verify spell preparation and slot expenditure via frontdoor REST."""
    char_id = created_character_id
    client.post(f"/api/v1/characters/{char_id}/level-up")

    prep_resp = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Magic Missile", "spell_level": 1},
    )
    assert prep_resp.status_code == 200
    assert "Magic Missile" in prep_resp.json()["prepared_spells"]

    cast_resp = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Magic Missile", "slot_level": 1},
    )
    assert cast_resp.status_code == 200
