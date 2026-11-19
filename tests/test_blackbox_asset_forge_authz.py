"""Blackbox frontdoor tests for Asset Forge creator identity and campaign authorization (TASK-0556).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup), ADR-0001 and ADR-0014.

- Requests go through the public HTTP routes with signed bearer tokens.
- Assertions read the HTTP responses, the Silo boundary and the forged asset GET projections.
- Campaign roles are written on the shared SpiceDB mock (the SpiceDB process boundary). Asset
  forge takes a UUID campaign id, and the gateway campaign flow issues other ids, so no frontdoor
  creates a UUID campaign for these tests.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from asset_forge.dependencies import get_event_bus, set_event_bus
from asset_forge.main import app
from fastapi.testclient import TestClient
from runefoble_auth.errors import AuthzWriteError
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.ws_identity import bearer

DM = "dm-evelyn"
PLAYER = "player-marcus"
SPECTATOR = "spectator-iris"
STRANGER = "stranger-mallory"
ROUTES = {
    "battlemap": "/api/v1/forge/battlemap",
    "token": "/api/v1/forge/token",
    "wardrobe": "/api/v1/forge/wardrobe",
    "print-pdf": "/api/v1/forge/print-pdf",
    "standees": "/api/v1/forge/standees",
    "stl-token": "/api/v1/forge/stl-token",
}


def _body(kind: str, campaign_id: str | None) -> dict:
    """Return a minimal valid request body for each forge route."""
    bodies = {
        "battlemap": {"prompt": "Flooded crypt with sunken altars", "width_cells": 10},
        "token": {"token_name": "Ghoul", "prompt": "Gaunt ghoul with rusted claws"},
        "wardrobe": {
            "character_id": str(uuid4()),
            "character_name": "Nadia",
            "attire_type": "arctic_tundra",
        },
        "print-pdf": {"prompt": "Dwarven forge", "width_cells": 10, "height_cells": 10},
        "standees": {
            "sheet_title": "Goblin Pack",
            "standees": [{"name": "Goblin", "type": "monster", "hp": 7, "color": "#e76f51"}],
            "format": "json",
        },
        "stl-token": {"diameter_mm": 28.0, "height_mm": 6.0},
    }
    body = dict(bodies[kind])
    if campaign_id is not None:
        body["campaign_id"] = campaign_id
    return body


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
    """A campaign with a DM, a player and a spectator. The stranger holds no role."""
    campaign_id = str(uuid4())
    for relation, user in (
        ("dungeon_master", DM),
        ("player", PLAYER),
        ("spectator", SPECTATOR),
    ):
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


def test_anonymous_forge_request_is_refused(client: TestClient, campaign: str):
    """Without a verified bearer token, no forge route creates an asset."""
    response = client.post(ROUTES["battlemap"], json=_body("battlemap", campaign))

    assert response.status_code == 401, response.text


@pytest.mark.parametrize("kind", ["battlemap", "token", "wardrobe", "print-pdf", "stl-token"])
def test_forge_without_campaign_is_a_bad_request(client: TestClient, kind: str):
    """Every forge route names a campaign. A request with no campaign id returns 400."""
    response = client.post(ROUTES[kind], json=_body(kind, None), headers=bearer(PLAYER))

    assert response.status_code == 400, response.text


def test_spectator_cannot_forge_a_token(client: TestClient, campaign: str):
    """A spectator observes the campaign. Forging needs `campaign.play`, so the request gets 403."""
    response = client.post(
        ROUTES["token"], json=_body("token", campaign), headers=bearer(SPECTATOR)
    )

    assert response.status_code == 403, response.text


def test_player_and_dm_can_forge_a_token(client: TestClient, campaign: str):
    """A player and the DM both hold `campaign.play`, so both get 200."""
    for user in (PLAYER, DM):
        response = client.post(ROUTES["token"], json=_body("token", campaign), headers=bearer(user))
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "forged"


def test_creator_is_the_verified_subject_not_a_header(client: TestClient, campaign: str):
    """A forged x-user-id header does not change who owns the asset. The token subject owns it."""
    headers = {**bearer(PLAYER), "x-user-id": STRANGER}
    created = client.post(ROUTES["token"], json=_body("token", campaign), headers=headers)
    assert created.status_code == 200, created.text
    asset_id = created.json()["asset_id"]

    # The stranger holds no campaign role and is not the creator, so the read is refused.
    refused = client.get(f"{ROUTES['token']}/{asset_id}", headers=bearer(STRANGER))
    assert refused.status_code == 403, refused.text

    # The creator reads the asset. The player also reads it through the campaign role.
    assert client.get(f"{ROUTES['token']}/{asset_id}", headers=bearer(PLAYER)).status_code == 200


def test_campaign_spectator_can_read_a_forged_battlemap(client: TestClient, campaign: str):
    """`forged_asset.view` walks to `campaign.view`, so a spectator reads a campaign asset."""
    created = client.post(
        ROUTES["battlemap"], json=_body("battlemap", campaign), headers=bearer(DM)
    )
    assert created.status_code == 200, created.text
    asset_id = created.json()["asset_id"]

    read = client.get(f"{ROUTES['battlemap']}/{asset_id}", headers=bearer(SPECTATOR))
    assert read.status_code == 200, read.text
    assert read.json()["asset_id"] == asset_id


def test_read_of_unknown_asset_is_not_found_before_authorization(client: TestClient):
    """A missing asset answers 404, so the route does not reveal permission state for it."""
    response = client.get(f"{ROUTES['battlemap']}/map-does-not-exist", headers=bearer(STRANGER))

    assert response.status_code == 404, response.text


def test_failed_relation_write_returns_503_and_stores_nothing(
    client: TestClient, campaign: str, spicedb, silo_double, monkeypatch
):
    """A SpiceDB write that fails returns 503. The Silo boundary receives no object."""

    async def refuse_write(**_kwargs):
        raise AuthzWriteError("SpiceDB did not apply the relationship write")

    monkeypatch.setattr(spicedb, "write_relationship", refuse_write)

    response = client.post(ROUTES["token"], json=_body("token", campaign), headers=bearer(PLAYER))

    assert response.status_code == 503, response.text
    assert "asset_id" not in response.json()
    assert silo_double.objects == {}


def test_old_assets_prefix_is_no_longer_mounted(client: TestClient, campaign: str):
    """Each forge route has one public prefix, `/api/v1/forge`. The old `/assets` mount is gone."""
    response = client.post(
        "/assets/print-pdf", json=_body("print-pdf", campaign), headers=bearer(PLAYER)
    )

    assert response.status_code == 404, response.text
