"""Blackbox frontdoor tests for rhetoric moves, temperament, and patience degradation.

Part of TASK-0281 / TASK-0262 / PRD-0024 / US-0075.
Governed by ADR-0001, ADR-0002, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.ws_identity import SIGNING_ISSUER

from .conftest import create_test_establishment

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.mark.asyncio
async def test_blackbox_patience_depletion_and_ejection(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify that failing aggressive intimidation depletes patience and terminates the interaction."""
    owner_id = f"owner_{uuid4().hex[:8]}"
    player_id = f"player_{uuid4().hex[:8]}"
    campaign_id = create_campaign(client, owner_id)
    invite_and_join(client, campaign_id, owner_id, player_id)
    establishment_id = create_test_establishment(client, campaign_id, owner_id)

    start_data = {
        "character_id": "char_krag",
        "item_id": "gem_ruby",
        "item_name": "Flawless Ruby",
        "base_price": 500,
        "initial_offer_gp": 200,
        "campaign_id": campaign_id,
        "establishment_id": establishment_id,
        "temperament": "Stubborn",
    }
    start_res = client.post(
        "/api/v1/haggling/start",
        json=start_data,
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_id)}"},
    )
    assert start_res.status_code == 200
    negotiation_id = start_res.json()["negotiation_id"]
    assert start_res.json()["patience"] == 5

    # 1. Fail intimidation roll twice (roll 2 vs DC 17 -> -2 patience each)
    for roll in (2, 3):
        res = client.post(
            f"/api/v1/haggling/{negotiation_id}/gambit",
            json={"character_id": "char_krag", "gambit": "hard_intimidation", "roll_value": roll},
            headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_id)}"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "active"

    # 2. Final failed gambit empties patience and kicks player out
    res3 = client.post(
        f"/api/v1/haggling/{negotiation_id}/gambit",
        json={"character_id": "char_krag", "gambit": "point_out_flaw", "roll_value": 4},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_id)}"},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["patience"] == 0
    assert data3["status"] == "refused"
    bark_lower = data3["last_bark"].lower()
    assert "patience is at its end" in bark_lower or "shop" in bark_lower

    # 3. Subsequent gambit is rejected with error
    subsequent_res = client.post(
        f"/api/v1/haggling/{negotiation_id}/gambit",
        json={"character_id": "char_krag", "gambit": "flattery", "roll_value": 20},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_id)}"},
    )
    assert subsequent_res.status_code == 400


@pytest.mark.asyncio
async def test_blackbox_walk_away_bluff_and_deal_acceptance(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Verify walk-away bluff discounts counter-offer and player can accept deal."""
    owner_id = f"owner_{uuid4().hex[:8]}"
    player_id = f"player_{uuid4().hex[:8]}"
    campaign_id = create_campaign(client, owner_id)
    invite_and_join(client, campaign_id, owner_id, player_id)
    establishment_id = create_test_establishment(client, campaign_id, owner_id)

    start_data = {
        "character_id": "char_lyra",
        "item_id": "elven_cloak",
        "item_name": "Elven Cloak",
        "base_price": 200,
        "initial_offer_gp": 120,
        "campaign_id": campaign_id,
        "establishment_id": establishment_id,
        "temperament": "Greedy",
    }
    start_res = client.post(
        "/api/v1/haggling/start",
        json=start_data,
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_id)}"},
    )
    assert start_res.status_code == 200
    neg_id = start_res.json()["negotiation_id"]

    bluff_res = client.post(
        f"/api/v1/haggling/{neg_id}/gambit",
        json={"character_id": "char_lyra", "gambit": "walk_away_bluff", "roll_value": 18},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_id)}"},
    )
    assert bluff_res.status_code == 200
    bluff_data = bluff_res.json()
    assert bluff_data["counter_price"] < 200

    accept_res = client.post(
        f"/api/v1/haggling/{neg_id}/accept",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player_id)}"},
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "completed"
