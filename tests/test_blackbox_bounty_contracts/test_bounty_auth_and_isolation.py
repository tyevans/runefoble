"""Blackbox tests for SpiceDB Zanzibar object authorization on bounty contracts.

Governed by ADR-0001, ADR-0005, and Hard Invariant 1.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

from .conftest import create_campaign_session, join_campaign

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.mark.asyncio
async def test_spicedb_zanzibar_permission_enforcement(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
) -> None:
    poster_id = "user_authorized_poster"
    unauthorized_user = "user_intruder"
    claimant_id = "user_mercenary_drake"
    dm_id = "user_session_dm"

    # The DM owns the campaign and its session. Poster and claimant join as players.
    campaign_id, session_id = create_campaign_session(client, dm_id)
    join_campaign(client, campaign_id, dm_id, poster_id)
    join_campaign(client, campaign_id, dm_id, claimant_id)

    # 1. Intruder cannot post bounty in session without participate permission
    res_unauth_post = client.post(
        f"/sessions/{session_id}/contracts/bounties",
        json={
            "title": "Unauthorized Bounty",
            "target_name": "Cave Troll",
            "escrow_gold": 100,
        },
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(unauthorized_user)}"},
    )
    assert res_unauth_post.status_code == 403

    # Poster is a player and posts the bounty
    res_post = client.post(
        f"/api/v1/sessions/{session_id}/contracts/bounties",  # Also verifies /api/v1 route alias
        json={
            "title": "Clear Goblin Warrens",
            "target_name": "Goblin Shaman",
            "escrow_gold": 300,
        },
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(poster_id)}"},
    )
    assert res_post.status_code == 201
    bounty_id = res_post.json()["bounty"]["bounty_id"]

    # 2. Intruder cannot view without view/observe permissions
    res_unauth_view = client.get(
        f"/sessions/{session_id}/contracts/bounties",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(unauthorized_user)}"},
    )
    assert res_unauth_view.status_code == 403

    # 3. Intruder cannot claim bounty without participate/claim permissions
    res_unauth_claim = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/claim",
        json={"claimant_party_name": "Rogue Band"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(unauthorized_user)}"},
    )
    assert res_unauth_claim.status_code == 403

    # Claimant is a player and claims the bounty
    res_claim = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/claim",
        json={"claimant_party_name": "Drake's Rangers"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(claimant_id)}"},
    )
    assert res_claim.status_code == 200

    # 4. Intruder cannot complete / disburse escrow
    res_unauth_comp = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/complete",
        json={"proof": "Faked Goblin Staff"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(unauthorized_user)}"},
    )
    assert res_unauth_comp.status_code == 403

    # 5. DM (campaign owner, session control) can complete and disburse
    res_dm_comp = client.post(
        f"/api/v1/sessions/{session_id}/contracts/bounties/{bounty_id}/complete",
        json={"proof": "Goblin Shaman's Staff verified by DM"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_id)}"},
    )
    assert res_dm_comp.status_code == 200
    assert res_dm_comp.json()["status"] == "COMPLETED"
    assert res_dm_comp.json()["payout"]["gold"] == 300
