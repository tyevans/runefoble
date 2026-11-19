"""Blackbox tests: a combine is one attempt that the character applies exactly once (TASK-0772).

Governed by ADR-0011 (Commands across two aggregates), ADR-0015 (f) and Hard Invariant 7. Setup
goes through the public character and crafting routes. A store failure uses the provider seam
(`store_append_outage`), not application code. Assertions read public responses and the events
on the character stream.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from character_sheet.dependencies import STREAM_CHARACTER
from fastapi.testclient import TestClient

from tests.helpers.event_store_seam import store_append_outage

REAGENTS = ["Volcano Ash", "Wyrm Blood"]
MISHAP_DAMAGE = 2  # caustic_fumes, the mishap that the risk of REAGENTS selects.
HEALTH_CHANGED = "runefoble.events.character.health_changed"


def _health_events(mock_bus: Any, char_id: str) -> list[dict[str, Any]]:
    found = []
    for _entry_id, fields in mock_bus.streams.get(STREAM_CHARACTER, []):
        if fields.get("event_type") == HEALTH_CHANGED:
            payload = json.loads(fields["payload"])
            if payload.get("aggregate_id") == char_id:
                found.append(payload)
    return found


def _create_character_with_reagents(char_client: TestClient) -> str:
    res = char_client.post(
        "/api/v1/characters",
        json={"name": "Apprentice", "character_class": "Wizard", "max_hp": 16},
    )
    assert res.status_code == 200, res.text
    char_id = res.json()["character_id"]
    for name in REAGENTS:
        added = char_client.post(
            f"/api/v1/characters/{char_id}/inventory",
            json={"item_id": str(uuid4()), "name": name, "quantity": 1},
        )
        assert added.status_code == 200, added.text
    return char_id


def _combine(char_client: TestClient, char_id: str, attempt_id: str | None = None) -> Any:
    body: dict[str, Any] = {
        "character_id": char_id,
        "reagents": REAGENTS,
        "force_mishap": True,
    }
    if attempt_id is not None:
        body["attempt_id"] = attempt_id
    return char_client.post("/api/v1/crafting/recipes/combine", json=body)


def _hp(char_client: TestClient, char_id: str) -> int:
    res = char_client.get(f"/api/v1/characters/{char_id}")
    assert res.status_code == 200, res.text
    return res.json()["current_hp"]


def _total_crafts(char_client: TestClient, char_id: str) -> int:
    res = char_client.get(f"/api/v1/crafting/{char_id}/history")
    assert res.status_code == 200, res.text
    return res.json()["total_crafts"]


def _inventory_names(char_client: TestClient, char_id: str) -> list[str]:
    """Add a marker item and read the names back from the state that the write returns."""
    res = char_client.post(
        f"/api/v1/characters/{char_id}/inventory",
        json={"item_id": str(uuid4()), "name": "Marker", "quantity": 1},
    )
    assert res.status_code == 200, res.text
    return [item["name"] for item in res.json()["inventory"].values()]


def test_failed_character_save_keeps_the_outcome_pending_until_a_read(
    char_client: TestClient, mock_bus: Any
) -> None:
    """The crafting save commits the decision. The failed character save answers 503."""
    char_id = _create_character_with_reagents(char_client)

    with store_append_outage("CharacterSheet"):
        res = _combine(char_client, char_id, attempt_id=str(uuid4()))
    assert res.status_code == 503, res.text
    assert _total_crafts(char_client, char_id) == 1
    assert _health_events(mock_bus, char_id) == []

    # The next character read applies the pending outcome once.
    assert _hp(char_client, char_id) == 16 - MISHAP_DAMAGE
    assert _hp(char_client, char_id) == 16 - MISHAP_DAMAGE
    assert len(_health_events(mock_bus, char_id)) == 1
    names = _inventory_names(char_client, char_id)
    assert "Marker" in names
    assert "Volcano Ash" not in names


def test_retry_with_the_same_attempt_id_applies_damage_once(
    char_client: TestClient, mock_bus: Any
) -> None:
    """A retry with the same attempt id returns the recorded outcome and applies it once."""
    char_id = _create_character_with_reagents(char_client)
    attempt_id = str(uuid4())

    with store_append_outage("CharacterSheet"):
        failed = _combine(char_client, char_id, attempt_id=attempt_id)
    assert failed.status_code == 503, failed.text

    retry = _combine(char_client, char_id, attempt_id=attempt_id)
    assert retry.status_code == 200, retry.text
    body = retry.json()
    assert body["outcome"] == "mishap"
    assert body["character_current_hp"] == 16 - MISHAP_DAMAGE
    assert body["mishap"]["damage"] == MISHAP_DAMAGE

    assert _total_crafts(char_client, char_id) == 1
    assert _hp(char_client, char_id) == 16 - MISHAP_DAMAGE
    assert len(_health_events(mock_bus, char_id)) == 1
    names = _inventory_names(char_client, char_id)
    assert "Marker" in names
    assert "Volcano Ash" not in names and "Wyrm Blood" not in names


def test_repeat_with_the_same_attempt_id_spends_nothing_again(
    char_client: TestClient, mock_bus: Any
) -> None:
    """Two calls with one attempt id record one attempt and apply one mishap."""
    char_id = _create_character_with_reagents(char_client)
    attempt_id = str(uuid4())

    first = _combine(char_client, char_id, attempt_id=attempt_id)
    second = _combine(char_client, char_id, attempt_id=attempt_id)
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json() == first.json()

    assert _total_crafts(char_client, char_id) == 1
    assert _hp(char_client, char_id) == 16 - MISHAP_DAMAGE
    assert len(_health_events(mock_bus, char_id)) == 1


def test_retry_without_an_attempt_id_is_a_new_attempt(
    char_client: TestClient, mock_bus: Any
) -> None:
    """Without an attempt id, each call is a new attempt. The pending one still applies once."""
    char_id = _create_character_with_reagents(char_client)

    with store_append_outage("CharacterSheet"):
        failed = _combine(char_client, char_id)
    assert failed.status_code == 503, failed.text

    retry = _combine(char_client, char_id)
    assert retry.status_code == 200, retry.text

    assert _total_crafts(char_client, char_id) == 2
    # The pending attempt applies its damage, then the new attempt applies its own damage.
    assert _hp(char_client, char_id) == 16 - 2 * MISHAP_DAMAGE
    assert len(_health_events(mock_bus, char_id)) == 2
