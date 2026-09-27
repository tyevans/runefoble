"""Blackbox tests for collaborative codex and entity cross-linking.

Governed by ADR-0001, ADR-0007, and Hard Invariant 7.
"""

from uuid import UUID, uuid4

import pytest
from campaign_lore.dependencies import get_codex_repo, get_retrieval_engine
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient


@pytest.mark.asyncio
async def test_codex_entity_cross_linking_and_privacy(
    client: TestClient, spicedb: SpiceDBClient, campaign_id: str
):
    """Test codex entity linking against redstring graph and Zanzibar access control."""
    rowan, bob = "rowan_chronicler", "bob_player"
    base = f"/api/v1/campaigns/{campaign_id}/codex/entries"
    r_h, b_h = {"x-user-id": rowan}, {"x-user-id": bob}

    await get_retrieval_engine().ingest_document(
        uuid4(),
        UUID(campaign_id),
        "Arcane Factions",
        "The Order of the Obsidian Veil is secretive.",
    )
    for uid in (rowan, bob):
        await spicedb.write_relationship("campaign", campaign_id, "player", "user", uid)

    resp = client.post(
        base,
        json={
            "title": "Secret Hypothesis",
            "content": "The Order of the Obsidian Veil.",
            "privacy": "private",
        },
        headers=r_h,
    )
    assert resp.status_code == 201
    entry_id = resp.json()["entry_id"]
    entry_url = f"{base}/{entry_id}"
    assert any("Order of the Obsidian Veil" in e["name"] for e in resp.json()["linked_entities"])
    assert "Order of the Obsidian Veil](#lore/entity/" in resp.json()["illuminated_content"]

    agg = await get_codex_repo().load(UUID(entry_id))
    assert agg.state.title == "Secret Hypothesis"

    # Access control: author allowed, other party member forbidden
    assert client.get(entry_url, headers=r_h).status_code == 200
    assert client.get(entry_url, headers=b_h).status_code == 403

    # Bob's listing excludes private entry, Rowan's includes it
    assert entry_id not in [e["entry_id"] for e in client.get(base, headers=b_h).json()]
    assert entry_id in [e["entry_id"] for e in client.get(base, headers=r_h).json()]

    # Share with party
    patch_resp = client.patch(entry_url, json={"privacy": "party_shared"}, headers=r_h)
    assert patch_resp.status_code == 200 and patch_resp.json()["privacy"] == "party_shared"

    assert client.get(entry_url, headers=b_h).status_code == 200
    assert entry_id in [e["entry_id"] for e in client.get(base, headers=b_h).json()]


def test_ui_manifest_advertises_atlas_and_codex(client: TestClient):
    """Test /ui/manifest advertises atlas and codex components."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "campaign_lore"
    assert "runefoble-campaign-atlas" in data["components"]
    assert "runefoble-campaign-codex" in data["components"]
