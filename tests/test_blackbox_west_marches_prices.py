"""Blackbox tests for West Marches outpost facility prices (TASK-0786).

An outpost upgrade spends the tier price from the outpost stored resources. A shortfall
answers 409 and changes nothing. The default outpost starts with 100 gold, 20 timber,
and 15 stone.

Governed by ADR-0003, ADR-0007, and Hard Invariant 7 (Blackbox TDD with frontdoor setup).
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.dependencies import set_west_marches_repo
from campaign_lore.main import app as lore_app
from campaign_lore.west_marches_aggregate import WestMarchesAtlasAggregate
from fastapi.testclient import TestClient
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_platform.event_sourcing import create_aggregate_repository

from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import bearer

PLAYER = "smith_mira"


@pytest.fixture
def spicedb_client() -> Iterator[MockSpiceDBClient]:
    mock_db = MockSpiceDBClient()
    with shared_spicedb_client(mock_db):
        yield mock_db


@pytest.fixture
def client(spicedb_client: MockSpiceDBClient, lore_backends) -> Iterator[TestClient]:
    set_west_marches_repo(create_aggregate_repository(WestMarchesAtlasAggregate))
    with TestClient(lore_app, headers=bearer(PLAYER)) as lore_client:
        yield lore_client


def _outpost(client: TestClient, cid: str) -> dict:
    overview = client.get(f"/api/v1/campaigns/{cid}/west-marches", headers=bearer(PLAYER))
    assert overview.status_code == 200, overview.text
    return next(iter(overview.json()["outposts"].values()))


@pytest.mark.asyncio
async def test_outpost_upgrade_spends_the_table_cost(
    client: TestClient, spicedb_client: MockSpiceDBClient
) -> None:
    """A watchtower upgrade to tier 2 costs 40 gold and 8 timber from the stored resources."""
    cid = uuid4()
    await spicedb_client.write_relationship("campaign", str(cid), "player", "user", PLAYER)

    resp = client.post(
        f"/api/v1/campaigns/{cid}/west-marches/stronghold/upgrade",
        json={"facility_id": "watchtower"},
        headers=bearer(PLAYER),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["new_tier"] == 2

    stored = _outpost(client, str(cid))["stored_resources"]
    assert stored["gold"] == 60
    assert stored["timber"] == 12
    assert stored["stone"] == 15
    assert _outpost(client, str(cid))["facilities"]["watchtower"] == 2


@pytest.mark.asyncio
async def test_outpost_upgrade_shortfall_answers_409_and_changes_nothing(
    client: TestClient, spicedb_client: MockSpiceDBClient
) -> None:
    """Tier 3 costs 100 gold, and the store holds 60 after one upgrade. A refusal changes nothing."""
    cid = uuid4()
    await spicedb_client.write_relationship("campaign", str(cid), "player", "user", PLAYER)
    first = client.post(
        f"/api/v1/campaigns/{cid}/west-marches/stronghold/upgrade",
        json={"facility_id": "watchtower"},
        headers=bearer(PLAYER),
    )
    assert first.status_code == 200, first.text
    before = _outpost(client, str(cid))

    refused = client.post(
        f"/api/v1/campaigns/{cid}/west-marches/stronghold/upgrade",
        json={"facility_id": "watchtower"},
        headers=bearer(PLAYER),
    )
    assert refused.status_code == 409, refused.text

    after = _outpost(client, str(cid))
    assert after["facilities"]["watchtower"] == 2
    assert after["stored_resources"] == before["stored_resources"]
