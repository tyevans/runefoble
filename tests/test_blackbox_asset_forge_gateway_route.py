"""Blackbox tests: the gateway battlemap route returns the asset that the App Shell shows (TASK-0645).

The gateway is called through its public HTTP routes. asset_forge runs as a live loopback
upstream (tests/helpers/live_services.py). The campaign role lives in the SpiceDB mock. Each
assertion reads a public response: the forge reply, the durable asset read, and the streamed bytes.
Governed by ADR-0001, ADR-0013 and ADR-0014.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.ws_identity import bearer

PLAYER = "player-marcus"
STRANGER = "stranger-mallory"
PNG_SIGNATURE = b"\x89PNG"


@pytest.fixture
def campaign(spicedb) -> str:
    """A campaign whose player may forge. The stranger holds no role in it."""
    campaign_id = str(uuid4())
    asyncio.run(
        spicedb.write_relationship(
            resource_type="campaign",
            resource_id=campaign_id,
            relation="player",
            subject_type="user",
            subject_id=PLAYER,
        )
    )
    return campaign_id


@pytest.fixture
def gateway(asset_forge_upstream: str) -> Iterator[TestClient]:
    """Gateway client wired to a live asset_forge. The URL is set before the lifespan runs."""
    with TestClient(gateway_app) as client:
        yield client


def _battlemap_body(campaign_id: str) -> dict:
    return {
        "prompt": "crypt with three pillars",
        "width_cells": 12,
        "height_cells": 12,
        "campaign_id": campaign_id,
    }


def test_battlemap_forge_returns_an_asset_id_that_the_durable_read_returns(
    gateway: TestClient, campaign: str
) -> None:
    forged = gateway.post(
        "/api/v1/forge/battlemap", json=_battlemap_body(campaign), headers=bearer(PLAYER)
    )
    assert forged.status_code == 200, forged.text
    asset_id = forged.json()["asset_id"]
    assert forged.json()["image_url"], "the forge reply must carry the preview URL"

    durable = gateway.get(f"/api/v1/forge/battlemap/{asset_id}", headers=bearer(PLAYER))

    assert durable.status_code == 200, durable.text
    assert durable.json()["asset_id"] == asset_id


def test_forged_battlemap_bytes_stream_through_the_gateway_as_png(
    gateway: TestClient, campaign: str
) -> None:
    forged = gateway.post(
        "/api/v1/forge/battlemap", json=_battlemap_body(campaign), headers=bearer(PLAYER)
    )
    assert forged.status_code == 200, forged.text
    asset_id = forged.json()["asset_id"]

    streamed = gateway.get(f"/api/v1/assets/{asset_id}/stream", headers=bearer(PLAYER))

    assert streamed.status_code == 200, streamed.text
    assert streamed.headers["content-type"] == "image/png"
    assert streamed.content.startswith(PNG_SIGNATURE)


def test_stranger_cannot_forge_a_battlemap_through_the_gateway(
    gateway: TestClient, campaign: str
) -> None:
    res = gateway.post(
        "/api/v1/forge/battlemap", json=_battlemap_body(campaign), headers=bearer(STRANGER)
    )

    assert res.status_code == 403, res.text
    assert "asset_id" not in res.json()
