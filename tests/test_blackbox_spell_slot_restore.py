"""Blackbox TDD tests for restoring spent spell slots (TASK-0679).

Governed by Hard Invariant 7: all setup and assertions go through public HTTP frontdoors of the
character_sheet service (POST /api/v1/characters, POST .../level-up, POST .../spells/prepare,
POST .../spells/cast, POST .../spells/restore, GET /api/v1/characters/{id}). No backdoor writes.
"""

from character_sheet.main import app
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_events.events import SpellSlotsRestored

from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


client = TestClient(app, headers=auth_headers("character-owner"))


def _create_wizard(name: str) -> str:
    res = client.post(
        "/api/v1/characters",
        json={"name": name, "character_class": "Wizard", "max_hp": 18},
    )
    assert res.status_code == 200, res.text
    return res.json()["character_id"]


def _slots(payload: dict) -> dict[int, int]:
    return {int(k): v for k, v in payload["spell_slots"].items()}


def _cast_magic_missile(char_id: str) -> dict:
    res = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Magic Missile", "slot_level": 1},
    )
    assert res.status_code == 200, res.text
    return res.json()


def test_blackbox_restore_all_spell_slots_to_maximum():
    """Casting spends slots; restore without a body returns every level to its maximum."""
    char_id = _create_wizard("Restore Tester")
    client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Magic Missile", "spell_level": 1},
    )
    _cast_magic_missile(char_id)
    spent = _cast_magic_missile(char_id)
    assert _slots(spent)[1] == 0

    restore_res = client.post(f"/api/v1/characters/{char_id}/spells/restore")
    assert restore_res.status_code == 200, restore_res.text
    assert _slots(restore_res.json())[1] == 2

    get_res = client.get(f"/api/v1/characters/{char_id}")
    assert get_res.status_code == 200, get_res.text
    assert _slots(get_res.json())[1] == 2


def test_blackbox_restore_single_level_leaves_other_levels_unchanged():
    """A restore with slot_level restores only that level."""
    char_id = _create_wizard("Level Restore Tester")
    client.post(
        f"/api/v1/characters/{char_id}/level-up",
        json={"target_level": 3},
    )
    client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Magic Missile", "spell_level": 1},
    )
    client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Misty Step", "spell_level": 2},
    )
    _cast_magic_missile(char_id)
    _cast_magic_missile(char_id)
    cast_2nd = client.post(
        f"/api/v1/characters/{char_id}/spells/cast",
        json={"spell_name": "Misty Step", "slot_level": 2},
    )
    assert cast_2nd.status_code == 200, cast_2nd.text
    assert _slots(cast_2nd.json()) == {1: 2, 2: 1}

    restore_res = client.post(
        f"/api/v1/characters/{char_id}/spells/restore",
        json={"slot_level": 1},
    )
    assert restore_res.status_code == 200, restore_res.text
    assert _slots(restore_res.json()) == {1: 4, 2: 1}


def test_blackbox_restore_rejects_level_the_character_does_not_have():
    """A slot level outside the character's spell slot table returns HTTP 400."""
    char_id = _create_wizard("Invalid Level Tester")
    res = client.post(
        f"/api/v1/characters/{char_id}/spells/restore",
        json={"slot_level": 7},
    )
    assert res.status_code == 400, res.text
    assert "INVALID_SPELL_SLOT_LEVEL" in res.json().get("detail", "")


def test_spell_slots_restored_event_is_registered():
    """The restore event is registered in the eventsource EventRegistry under its type name."""
    event_cls = get_event_class_or_none("runefoble.events.character.spell_slots_restored")
    assert event_cls is SpellSlotsRestored
