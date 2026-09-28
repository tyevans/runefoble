"""Blackbox TDD tests for conditions, DM penalties, spell preparation, and slots.

Governed by ADR-0003, ADR-0004, ADR-0007, ADR-0013, and Hard Invariant 7.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import REPO_ROOT


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


def test_conditions_spells_components_and_invariants() -> None:
    """Verify action handlers, condition types, and file length invariant limits."""
    ui_dir = REPO_ROOT / "services/character_sheet/ui"
    actions_src = (ui_dir / "src/runefoble-character-sheet.actions.ts").read_text(encoding="utf-8")
    for act in (
        "castSpellSlot",
        "togglePreparedSpell",
        "applyConditionToState",
        "toggleSpellSlotPip",
    ):
        assert act in actions_src

    types_src = (ui_dir / "src/runefoble-character-sheet.types.ts").read_text(encoding="utf-8")
    assert "blinded" in types_src and "drunk" in types_src

    styles_src = (ui_dir / "src/runefoble-character-sheet.conditions.styles.ts").read_text(
        encoding="utf-8"
    )
    assert "condition-badge" in styles_src

    # Invariant: all test sub-modules strictly < 130 lines per Hard Invariant 6
    test_dir = REPO_ROOT / "tests/test_blackbox_character_sheet_ui"
    for py_file in test_dir.glob("*.py"):
        lines = len(py_file.read_text(encoding="utf-8").splitlines())
        assert lines < 130, f"{py_file.name} exceeded 130 lines ({lines})"
