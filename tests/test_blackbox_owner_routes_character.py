"""Blackbox frontdoor test for the `clear_condition` owner route (TASK-0846 part a).

The route is called through `runefoble_platform.service_client.owner_routes`. The character
owner removes a condition and the owner publishes `condition_removed`. A caller without
`character.edit` gets 403 and no event. Setup uses only public character routes.
"""

from __future__ import annotations

import json

import pytest
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from runefoble_platform.service_client import owner_routes

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

OWNER = "owner_clear_condition"
STRANGER = "stranger_clear_condition"
CONDITION_REMOVED = "runefoble.events.character.condition_removed"


@pytest.fixture
def character_client() -> TestClient:
    return TestClient(character_app)


def _create_poisoned_character(client: TestClient) -> str:
    created = client.post(
        "/api/v1/characters",
        json={
            "name": "Valeros",
            "character_class": "Fighter 4",
            "max_hp": 38,
            "armor_class": 18,
            "speed": 30,
        },
        headers=bearer(OWNER),
    )
    assert created.status_code == 200, created.text
    character_id = created.json()["character_id"]
    applied = client.post(
        f"/api/v1/characters/{character_id}/conditions",
        json={"condition": "poisoned", "source": "serpent_strike"},
        headers=bearer(OWNER),
    )
    assert applied.status_code == 200, applied.text
    assert "poisoned" in applied.json()["conditions"]
    return character_id


def _removed_conditions(mock_bus: MockAsyncRedis) -> list[dict]:
    payloads: list[dict] = []
    for entries in mock_bus.streams.values():
        for _entry_id, fields in entries:
            if fields.get("event_type") == CONDITION_REMOVED:
                payloads.append(json.loads(fields["payload"]))
    return payloads


def test_owner_clears_condition_and_owner_publishes_condition_removed(
    character_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    character_id = _create_poisoned_character(character_client)
    route = owner_routes.clear_condition(character_id, "poisoned")

    res = character_client.request(route.method, route.path, headers=bearer(OWNER))

    assert res.status_code == 200, res.text
    assert "poisoned" not in res.json()["conditions"]
    assert any(p.get("condition") == "poisoned" for p in _removed_conditions(mock_bus))


def test_stranger_cannot_clear_condition(
    character_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    character_id = _create_poisoned_character(character_client)
    before = len(_removed_conditions(mock_bus))
    route = owner_routes.clear_condition(character_id, "poisoned")

    res = character_client.request(route.method, route.path, headers=bearer(STRANGER))

    assert res.status_code == 403, res.text
    assert len(_removed_conditions(mock_bus)) == before
