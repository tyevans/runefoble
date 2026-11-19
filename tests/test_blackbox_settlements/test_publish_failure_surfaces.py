"""Blackbox tests: a save-then-publish route fails loudly when the stream is unreachable.

Governed by ADR-0011, ADR-0015 and Hard Invariant 7 (TASK-0858). The Redis double is the
process boundary. Setup and reads go through the public settlement routes.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

FOUNDER = "builder_orla"


class UnreachableRedis(MockAsyncRedis):
    """A Redis double whose stream writes fail, as when the broker is down."""

    async def xadd(self, stream: str, fields: dict[str, Any]) -> str:
        raise ConnectionError("redis unreachable")


async def _charter_haven(client: TestClient, spicedb: MockSpiceDBClient) -> str:
    camp = str(uuid4())
    world = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Ashen Vale", "frontier_region": "Cinder Hills"},
        headers=bearer(FOUNDER),
    )
    world_id = world.json()["shared_world_id"]
    await spicedb.write_relationship("shared_world", world_id, "participant", "user", FOUNDER)
    await spicedb.write_relationship("campaign", camp, "player", "user", FOUNDER)
    charter = client.post(
        "/api/v1/settlements",
        json={"name": "Cinder Hold", "shared_world_id": world_id, "founded_by_campaign_id": camp},
        headers=bearer(FOUNDER),
    )
    assert charter.status_code == 201, charter.text
    return charter.json()["settlement_id"]


@pytest.mark.asyncio
async def test_unreachable_stream_answers_503_and_keeps_the_saved_state(
    client: TestClient,
    spicedb: MockSpiceDBClient,
    use_redis_client: Any,
) -> None:
    """A deposit that cannot publish answers 503. The saved treasury stays visible."""
    sid = await _charter_haven(client, spicedb)

    use_redis_client(UnreachableRedis())
    deposit = client.post(
        f"/api/v1/settlements/{sid}/deposit",
        json={"gold": 500, "materials": {}},
        headers=bearer(FOUNDER),
    )
    assert deposit.status_code == 503, deposit.text

    view = client.get(f"/api/v1/settlements/{sid}", headers=bearer(FOUNDER))
    assert view.status_code == 200
    assert view.json()["gold_treasury"] == 500
