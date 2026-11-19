"""Blackbox frontdoor tests: every forge record belongs to a named campaign (TASK-0902).

Governed by Hard Invariant 7, ADR-0011 and ADR-0015 (no random substitute ids).

- A forge request without `campaign_id` fails validation with 422. No record is saved.
- A forge request with a campaign saves the record in the campaign forge aggregate.
  The public campaign record list `GET /api/v1/forge/campaigns/{campaign_id}/records` shows it.
- Campaign roles are written on the shared SpiceDB mock (the SpiceDB process boundary).
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from asset_forge.dependencies import get_event_bus, set_event_bus
from asset_forge.main import app
from fastapi.testclient import TestClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.ws_identity import bearer

PLAYER = "player-marcus"
SPECTATOR = "spectator-iris"
STRANGER = "stranger-mallory"

FORGE_BODIES = {
    "/api/v1/forge/battlemap": {"prompt": "Flooded crypt with sunken altars", "width_cells": 10},
    "/api/v1/forge/token": {"token_name": "Ghoul", "prompt": "Gaunt ghoul with rusted claws"},
    "/api/v1/forge/wardrobe": {
        "character_id": str(uuid4()),
        "character_name": "Nadia",
        "attire_type": "arctic_tundra",
    },
    "/api/v1/forge/print-pdf": {
        "prompt": "Dwarven forge",
        "width_cells": 10,
        "height_cells": 10,
        "format": "json",
    },
    "/api/v1/forge/standees": {
        "sheet_title": "Goblin Pack",
        "standees": [{"name": "Goblin", "type": "monster", "hp": 7, "color": "#e76f51"}],
        "format": "json",
    },
    "/api/v1/forge/stl-token": {"diameter_mm": 28.0, "height_mm": 6.0, "format": "json"},
}


def _records_url(campaign_id: str) -> str:
    return f"/api/v1/forge/campaigns/{campaign_id}/records"


@pytest.fixture(autouse=True)
def clean_environment(seam_restorer: SeamRestorer):
    """Start every test with a Redis Streams bus over a mock, then restore the previous bus."""
    seam_restorer.replace(
        get_event_bus, set_event_bus, RedisStreamsEventBus(client=MockAsyncRedis())
    )
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def campaign(spicedb) -> str:
    """A campaign with a player and a spectator. The stranger holds no role."""
    campaign_id = str(uuid4())
    for relation, user in (("player", PLAYER), ("spectator", SPECTATOR)):
        asyncio.run(
            spicedb.write_relationship(
                resource_type="campaign",
                resource_id=campaign_id,
                relation=relation,
                subject_type="user",
                subject_id=user,
            )
        )
    return campaign_id


@pytest.mark.parametrize("route", sorted(FORGE_BODIES))
def test_forge_request_without_campaign_fails_validation(client: TestClient, route: str):
    """The campaign id is a required field. A request without it answers 422 and names it."""
    response = client.post(route, json=FORGE_BODIES[route], headers=bearer(PLAYER))

    assert response.status_code == 422, response.text
    fields = [error["loc"][-1] for error in response.json()["detail"]]
    assert "campaign_id" in fields


def test_new_campaign_has_no_forge_records(client: TestClient, campaign: str):
    """A campaign with no forge request answers an empty record list, not 404."""
    response = client.get(_records_url(campaign), headers=bearer(PLAYER))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["campaign_id"] == campaign
    assert body["records"] == []


def test_forged_assets_show_in_the_campaign_record_list(client: TestClient, campaign: str):
    """Each forge request with a campaign saves one record. The campaign list shows each one."""
    forged: dict[str, str] = {}
    for route, payload in FORGE_BODIES.items():
        if route.endswith("/wardrobe"):
            continue  # Wardrobe variants are character portraits, not campaign forge records.
        response = client.post(
            route, json={**payload, "campaign_id": campaign}, headers=bearer(PLAYER)
        )
        assert response.status_code == 200, response.text
        forged[response.json()["asset_id"]] = route

    listing = client.get(_records_url(campaign), headers=bearer(SPECTATOR))

    assert listing.status_code == 200, listing.text
    records = listing.json()["records"]
    assert {record["asset_id"] for record in records} == set(forged)
    assert {record["campaign_id"] for record in records} == {campaign}
    kinds = {record["asset_id"]: record["kind"] for record in records}
    assert kinds[next(a for a, r in forged.items() if r.endswith("/battlemap"))] == "battlemap"
    assert kinds[next(a for a, r in forged.items() if r.endswith("/token"))] == "token"
    assert kinds[next(a for a, r in forged.items() if r.endswith("/stl-token"))] == "stl_token"


def test_records_of_one_campaign_stay_out_of_another(client: TestClient, campaign: str, spicedb):
    """The record list reads one campaign aggregate. A forge in campaign A is not in campaign B."""
    other = str(uuid4())
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=other,
            relation="player",
            subject_type="user",
            subject_id=PLAYER,
        )
    )
    body = {**FORGE_BODIES["/api/v1/forge/token"], "campaign_id": campaign}
    assert client.post("/api/v1/forge/token", json=body, headers=bearer(PLAYER)).status_code == 200

    listing = client.get(_records_url(other), headers=bearer(PLAYER))

    assert listing.status_code == 200, listing.text
    assert listing.json()["records"] == []


def test_stranger_cannot_read_campaign_records(client: TestClient, campaign: str):
    """The record list needs `campaign.view`. A caller with no campaign role gets 403."""
    response = client.get(_records_url(campaign), headers=bearer(STRANGER))

    assert response.status_code == 403, response.text


def test_campaign_records_need_a_uuid_campaign_id(client: TestClient):
    """The path takes a strict UUID campaign id (ADR-0015). Another value answers 422."""
    response = client.get(_records_url("not-a-uuid"), headers=bearer(PLAYER))

    assert response.status_code == 422, response.text
