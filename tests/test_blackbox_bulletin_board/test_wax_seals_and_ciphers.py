"""Blackbox tests for wax-sealed notices and cipher decryption workflows.

Part of TASK-0276 / PRD-0024 / US-0076. Governed by ADR-0001, ADR-0002, ADR-0008.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.mock_redis import MockAsyncRedis

from .conftest import assert_event_emitted


@pytest.mark.asyncio
async def test_blackbox_wax_sealed_ordinance_posting(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Pin and inspect a wax-sealed civic proclamation."""
    cid, mayor = str(uuid4()), f"m_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "player", "user", mayor)

    res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Highspire Haven", "scale": "village"},
        headers={"x-user-id": mayor},
    )
    sid = res.json()["settlement_id"]
    base_url = f"/api/v1/settlements/{sid}/bulletin"

    ord_payload = {
        "board_type": "town_square",
        "title": "Curfew",
        "category": "ordinance",
        "content": "Gates lock.",
        "wax_sealed": True,
    }
    ord_res = client.post(base_url, json=ord_payload, headers={"x-user-id": mayor})
    assert ord_res.status_code == 201 and ord_res.json()["wax_sealed"] is True

    notices = client.get(base_url, headers={"x-user-id": mayor}).json()
    assert len(notices) == 1 and notices[0]["wax_sealed"] is True


@pytest.mark.asyncio
async def test_blackbox_cipher_notice_decryption_workflow(
    client: TestClient, spicedb: MockSpiceDBClient, mock_bus: MockAsyncRedis
) -> None:
    """Pin cipher notice, verify masking, submit decryption, and verify unlocked content."""
    cid = str(uuid4())
    rogue, sleuth, spectator = (
        f"r_{uuid4().hex[:8]}",
        f"s_{uuid4().hex[:8]}",
        f"p_{uuid4().hex[:8]}",
    )
    for uid in (rogue, sleuth, spectator):
        await spicedb.write_relationship("campaign", cid, "player", "user", uid)

    res = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Shadowport Haven", "scale": "village"},
        headers={"x-user-id": rogue},
    )
    sid = res.json()["settlement_id"]
    base_url = f"/api/v1/settlements/{sid}/bulletin"

    secret = "Midnight rendezvous at the Gilded Serpent back alley."
    cipher_payload = {
        "board_type": "tavern",
        "title": "Cant",
        "category": "rumor",
        "content": "Seek the shadow.",
        "cipher_encoded": True,
        "cipher_puzzle": "rot13",
        "cipher_solution": "gilded serpent",
        "hidden_content": secret,
    }
    pin = client.post(base_url, json=cipher_payload, headers={"x-user-id": rogue})
    nid = pin.json()["notice_id"]
    decrypt_url = f"{base_url}/{nid}/decrypt"

    # Secret is masked before solve
    sleuth_view = client.get(base_url, headers={"x-user-id": sleuth}).json()
    n = next(x for x in sleuth_view if x["notice_id"] == nid)
    assert n["is_decrypted"] is False and n["hidden_content"] is None

    # Incorrect solution -> 400 Bad Request
    fail_res = client.post(decrypt_url, json={"solution": "wrong"}, headers={"x-user-id": sleuth})
    assert fail_res.status_code == 400

    # Correct solution -> 200 OK and revealed
    solve = client.post(
        decrypt_url, json={"solution": "gilded serpent"}, headers={"x-user-id": sleuth}
    )
    assert solve.status_code == 200 and solve.json()["decrypted_content"] == secret
    assert_event_emitted(mock_bus, "CipherNoticeDecrypted")

    # Sleuth now sees hidden content; spectator still masked
    unlocked = client.get(base_url, headers={"x-user-id": sleuth}).json()
    assert next(x for x in unlocked if x["notice_id"] == nid)["hidden_content"] == secret

    spec = client.get(base_url, headers={"x-user-id": spectator}).json()
    assert next(x for x in spec if x["notice_id"] == nid)["hidden_content"] is None
