"""Blackbox tests: combining reagents fails loudly and publishes the standard health events.

Governed by ADR-0011, ADR-0015 (f) and Hard Invariant 7 (TASK-0729). Setup goes through the
public crafting and character routes. Store failures use the provider seam (`store_outage`), not application code. Assertions read the public responses and the
events on the character and crafting streams.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from character_sheet.dependencies import STREAM_CHARACTER, STREAM_CRAFTING
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client

from tests.helpers.event_store_seam import store_outage

OUTAGE_DETAIL = "Event store is unavailable"
MISHAP_PAYLOAD_REAGENTS = ["Volcano Ash", "Wyrm Blood"]


def _events(mock_bus: Any, stream: str, event_type: str) -> list[dict[str, Any]]:
    """Return the decoded payloads of one event type on one stream."""
    found = []
    for _entry_id, fields in mock_bus.streams.get(stream, []):
        if fields.get("event_type") == event_type:
            found.append(json.loads(fields["payload"]))
    return found


def _create_character(char_client: TestClient, max_hp: int = 16) -> str:
    res = char_client.post(
        "/api/v1/characters",
        json={"name": "Apprentice", "character_class": "Wizard", "max_hp": max_hp},
    )
    assert res.status_code == 200, res.text
    return res.json()["character_id"]


def test_mishap_damage_publishes_the_standard_health_events(
    char_client: TestClient, mock_bus: Any
) -> None:
    """Mishap damage publishes CharacterHealthChanged and CharacterDamaged with the saved HP."""
    char_id = _create_character(char_client, max_hp=16)

    res = char_client.post(
        "/api/v1/crafting/recipes/combine",
        json={
            "character_id": char_id,
            "reagents": MISHAP_PAYLOAD_REAGENTS,
            "force_mishap": True,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["outcome"] == "mishap"
    damage = 16 - body["character_current_hp"]
    assert damage > 0

    changed = _events(mock_bus, STREAM_CHARACTER, "CharacterHealthChanged")
    mine = [e for e in changed if e.get("aggregate_id") == char_id]
    assert len(mine) == 1
    assert mine[0]["delta"] == -damage
    assert mine[0]["current_hp"] == body["character_current_hp"]
    assert mine[0]["source"] == "crafting_mishap"

    damaged = _events(mock_bus, STREAM_CHARACTER, "runefoble.events.character.damaged")
    assert [e["delta"] for e in damaged if e.get("character_id") == char_id] == [-damage]


def test_unknown_character_answers_404_and_writes_nothing(
    char_client: TestClient, mock_bus: Any
) -> None:
    """A character with no stream answers 404. No crafting event is published for it."""
    missing_id = str(uuid4())
    asyncio.run(
        get_spicedb_client().write_relationship(
            resource_type="character",
            resource_id=missing_id,
            relation="owner",
            subject_type="user",
            subject_id="character-owner",
        )
    )

    res = char_client.post(
        "/api/v1/crafting/recipes/combine",
        json={"character_id": missing_id, "reagents": MISHAP_PAYLOAD_REAGENTS},
    )
    assert res.status_code == 404, res.text

    crafted = _events(mock_bus, STREAM_CRAFTING, "CraftingAttempted")
    assert all(e.get("character_id") != missing_id for e in crafted)

    history = char_client.get(f"/api/v1/crafting/{missing_id}/history")
    assert history.status_code == 200, history.text
    assert history.json()["total_crafts"] == 0


def test_character_load_failure_answers_503_and_publishes_nothing(
    char_client: TestClient, mock_bus: Any
) -> None:
    """A failed character load answers 503. The combine saves and publishes nothing."""
    char_id = _create_character(char_client)

    with store_outage():
        res = char_client.post(
            "/api/v1/crafting/recipes/combine",
            json={"character_id": char_id, "reagents": MISHAP_PAYLOAD_REAGENTS},
        )
    assert res.status_code == 503, res.text
    assert res.json()["detail"] == OUTAGE_DETAIL

    assert _events(mock_bus, STREAM_CRAFTING, "CraftingAttempted") == []
    assert _events(mock_bus, STREAM_CRAFTING, "CraftingMishapOccurred") == []
    assert _events(mock_bus, STREAM_CHARACTER, "CharacterHealthChanged") == []

    history = char_client.get(f"/api/v1/crafting/{char_id}/history")
    assert history.status_code == 200, history.text
    assert history.json()["total_crafts"] == 0


def test_history_store_failure_answers_503_not_an_empty_state(char_client: TestClient) -> None:
    """A failed crafting load answers 503. It does not answer an empty history."""
    char_id = _create_character(char_client)

    with store_outage():
        res = char_client.get(f"/api/v1/crafting/{char_id}/history")
    assert res.status_code == 503, res.text
    assert res.json()["detail"] == OUTAGE_DETAIL
