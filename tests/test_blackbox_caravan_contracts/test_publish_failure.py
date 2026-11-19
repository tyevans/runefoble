"""Blackbox test: posting a caravan contract answers 503 when the stream is unreachable.

Governed by ADR-0011, ADR-0015 and Hard Invariant 7 (TASK-0886). The Redis double is the
process boundary. Setup and reads go through the public shared world and contract routes.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.helpers.campaign_setup import create_campaign
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

OFFICER = "guild_officer_ilse"


class UnreachableRedis(MockAsyncRedis):
    """A Redis double whose stream writes fail, as when the broker is down."""

    async def xadd(self, stream: str, fields: dict[str, Any]) -> str:
        raise ConnectionError("redis unreachable")


def test_contract_post_that_cannot_publish_answers_503_and_stays_on_the_board(
    client: TestClient, use_redis_client: Any
) -> None:
    """The contract is saved and listed. The client sees 503 for the failed publish."""
    h = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(OFFICER)}"}
    world = client.post(
        "/api/v1/shared-worlds",
        json={"name": "Grey Fens", "frontier_region": "Mire Coast"},
        headers=h,
    )
    assert world.status_code == 201, world.text
    world_id = world.json()["shared_world_id"]
    campaign = create_campaign(client, OFFICER)
    reg = client.post(
        f"/api/v1/shared-worlds/{world_id}/campaigns",
        json={"campaign_id": campaign, "party_name": "The Fen Wardens"},
        headers=h,
    )
    assert reg.status_code == 201, reg.text

    use_redis_client(UnreachableRedis())
    post = client.post(
        f"/api/v1/shared-worlds/{world_id}/caravans/contracts",
        json={
            "origin_outpost": "Reed Gate",
            "destination_outpost": "Saltmarsh",
            "cargo": {"peat": 30},
            "cargo_value": 120,
            "route_risk_level": "low",
            "transit_stages": 1,
            "escort_collateral": 10,
            "reward_gold": 60,
            "reward_reputation": 5,
            "posted_by_campaign_id": campaign,
            "expires_in_turns": 6,
        },
        headers=h,
    )
    assert post.status_code == 503, post.text

    board = client.get(f"/api/v1/shared-worlds/{world_id}/caravans/contracts", headers=h)
    assert board.status_code == 200
    assert [c["destination_outpost"] for c in board.json()["contracts"]] == ["Saltmarsh"]
