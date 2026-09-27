"""Blackbox tests for SpiceDB Zanzibar object authorization on bounty contracts.

Governed by ADR-0001, ADR-0005, and Hard Invariant 1.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis


@pytest.mark.asyncio
async def test_spicedb_zanzibar_permission_enforcement(
    client: TestClient,
    mock_bus: MockAsyncRedis,
    spicedb: MockSpiceDBClient,
) -> None:
    session_id = str(uuid4())
    poster_id = "user_authorized_poster"
    unauthorized_user = "user_intruder"
    claimant_id = "user_mercenary_drake"
    dm_id = "user_session_dm"

    # 1. Intruder cannot post bounty in session without participate permission
    res_unauth_post = client.post(
        f"/sessions/{session_id}/contracts/bounties",
        json={
            "title": "Unauthorized Bounty",
            "target_name": "Cave Troll",
            "escrow_gold": 100,
        },
        headers={"x-user-id": unauthorized_user},
    )
    assert res_unauth_post.status_code == 403

    # Grant permission to poster and post bounty
    await spicedb.write_relationship("session", session_id, "participate", "user", poster_id)
    res_post = client.post(
        f"/api/v1/sessions/{session_id}/contracts/bounties",  # Also verifies /api/v1 route alias
        json={
            "title": "Clear Goblin Warrens",
            "target_name": "Goblin Shaman",
            "escrow_gold": 300,
        },
        headers={"x-user-id": poster_id},
    )
    assert res_post.status_code == 201
    bounty_id = res_post.json()["bounty"]["bounty_id"]

    # 2. Intruder cannot view without view/observe permissions
    res_unauth_view = client.get(
        f"/sessions/{session_id}/contracts/bounties",
        headers={"x-user-id": unauthorized_user},
    )
    assert res_unauth_view.status_code == 403

    # 3. Intruder cannot claim bounty without participate/claim permissions
    res_unauth_claim = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/claim",
        json={"claimant_party_name": "Rogue Band"},
        headers={"x-user-id": unauthorized_user},
    )
    assert res_unauth_claim.status_code == 403

    # Grant claimant participate permission and claim
    await spicedb.write_relationship("session", session_id, "participate", "user", claimant_id)
    res_claim = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/claim",
        json={"claimant_party_name": "Drake's Rangers"},
        headers={"x-user-id": claimant_id},
    )
    assert res_claim.status_code == 200

    # 4. Intruder cannot complete / disburse escrow
    res_unauth_comp = client.post(
        f"/sessions/{session_id}/contracts/bounties/{bounty_id}/complete",
        json={"proof": "Faked Goblin Staff"},
        headers={"x-user-id": unauthorized_user},
    )
    assert res_unauth_comp.status_code == 403

    # 5. DM with session control can complete and disburse
    await spicedb.write_relationship("session", session_id, "control", "user", dm_id)
    res_dm_comp = client.post(
        f"/api/v1/sessions/{session_id}/contracts/bounties/{bounty_id}/complete",
        json={"proof": "Goblin Shaman's Staff verified by DM"},
        headers={"x-user-id": dm_id},
    )
    assert res_dm_comp.status_code == 200
    assert res_dm_comp.json()["status"] == "COMPLETED"
    assert res_dm_comp.json()["payout"]["gold"] == 300
