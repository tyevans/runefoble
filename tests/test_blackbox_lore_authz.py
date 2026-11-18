"""Blackbox frontdoor tests: Campaign Lore authorization per schema permission (TASK-0553).

Governed by ADR-0001 (SpiceDB Zanzibar), ADR-0014 (frontdoor setup), and Hard Invariant 7.
Every request goes through public HTTP routes with a signed bearer token. Campaign Lore has
no membership frontdoor, so role tuples are written with schema relation names only.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.identity import set_zitadel_auth_service
from campaign_lore.main import app
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.ws_identity import SIGNING_ISSUER

SECRET_TEXT = "Dragon Eye gem vault beneath the Obsidian Citadel"


def _bearer(user_id: str, issuer: SigningTestIssuer = SIGNING_ISSUER) -> dict[str, str]:
    """Return headers carrying a signed bearer token for `user_id`."""
    return {"Authorization": f"Bearer {issuer.mint(user_id)}"}


@pytest.fixture(autouse=True)
def _trust_signing_issuer() -> Iterator[None]:
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    yield
    set_zitadel_auth_service(None)


@pytest.fixture
def client(lore_backends) -> Iterator[TestClient]:
    with TestClient(app) as lore_client:
        yield lore_client


@pytest.fixture
def spicedb() -> SpiceDBClient:
    return get_spicedb_client()


@pytest.fixture
def world(spicedb: SpiceDBClient) -> dict[str, str]:
    """Two campaigns. Each has a DM and a player. Campaign A also has a spectator."""
    ids = {
        "a": str(uuid4()),
        "b": str(uuid4()),
        "dm_a": f"dm-a-{uuid4().hex[:6]}",
        "player_a": f"player-a-{uuid4().hex[:6]}",
        "spectator_a": f"spectator-a-{uuid4().hex[:6]}",
        "dm_b": f"dm-b-{uuid4().hex[:6]}",
        "player_b": f"player-b-{uuid4().hex[:6]}",
    }
    return ids


async def _seed_roles(spicedb: SpiceDBClient, world: dict[str, str]) -> None:
    """Write role tuples with schema relation names. No membership frontdoor exists here."""
    roles = [
        (world["a"], "dungeon_master", world["dm_a"]),
        (world["a"], "player", world["player_a"]),
        (world["a"], "spectator", world["spectator_a"]),
        (world["b"], "dungeon_master", world["dm_b"]),
        (world["b"], "player", world["player_b"]),
    ]
    for campaign_id, relation, user_id in roles:
        await spicedb.write_relationship("campaign", campaign_id, relation, "user", user_id)


def _publish(client: TestClient, campaign_id: str, user_id: str, privacy: str) -> str:
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/codex/entries",
        json={
            "title": "Sunken Archive",
            "content": "Lore of the sunken archive.",
            "privacy": privacy,
        },
        headers=_bearer(user_id),
    )
    assert res.status_code == 201, res.text
    return res.json()["entry_id"]


@pytest.mark.asyncio
async def test_codex_entry_read_through_another_campaign_path_is_not_found(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """A party_shared entry of campaign B is invisible through campaign A's path (404)."""
    await _seed_roles(spicedb, world)
    entry_b = _publish(client, world["b"], world["dm_b"], "party_shared")

    # Player of A has play in A. Before the fix, A's path granted read of B's entry.
    via_a = client.get(
        f"/api/v1/campaigns/{world['a']}/codex/entries/{entry_b}",
        headers=_bearer(world["player_a"]),
    )
    assert via_a.status_code == 404, via_a.text

    # Same entry through its own campaign path is still readable by a player of B.
    via_b = client.get(
        f"/api/v1/campaigns/{world['b']}/codex/entries/{entry_b}",
        headers=_bearer(world["player_b"]),
    )
    assert via_b.status_code == 200, via_b.text


@pytest.mark.asyncio
async def test_codex_entry_edit_through_another_campaign_path_is_not_found(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """A DM of campaign A cannot edit campaign B's entry through A's path."""
    await _seed_roles(spicedb, world)
    entry_b = _publish(client, world["b"], world["dm_b"], "private")

    res = client.patch(
        f"/api/v1/campaigns/{world['a']}/codex/entries/{entry_b}",
        json={"title": "Rewritten by another campaign"},
        headers=_bearer(world["dm_a"]),
    )
    assert res.status_code == 404, res.text


@pytest.mark.asyncio
async def test_codex_publish_requires_a_verified_player(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """Anonymous publish returns 401. A spectator publish returns 403. A player publish returns 201."""
    await _seed_roles(spicedb, world)
    payload = {"title": "Anonymous Note", "content": "No identity.", "privacy": "private"}
    url = f"/api/v1/campaigns/{world['a']}/codex/entries"

    assert client.post(url, json=payload).status_code == 401
    spectator = client.post(url, json=payload, headers=_bearer(world["spectator_a"]))
    assert spectator.status_code == 403, spectator.text
    player = client.post(url, json=payload, headers=_bearer(world["player_a"]))
    assert player.status_code == 201, player.text
    assert player.json()["author_id"] == world["player_a"]


@pytest.mark.asyncio
async def test_codex_privacy_accepts_only_schema_values(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """A privacy value outside private, party_shared, and public is refused with 422."""
    await _seed_roles(spicedb, world)
    res = client.post(
        f"/api/v1/campaigns/{world['a']}/codex/entries",
        json={"title": "Odd Privacy", "content": "Body.", "privacy": "whatever"},
        headers=_bearer(world["dm_a"]),
    )
    assert res.status_code == 422, res.text


@pytest.mark.asyncio
async def test_party_shared_entry_is_readable_by_players_and_not_spectators(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """A DM publishes a party_shared entry. A player reads it (200). A spectator is refused (403)."""
    await _seed_roles(spicedb, world)
    entry = _publish(client, world["a"], world["dm_a"], "party_shared")
    url = f"/api/v1/campaigns/{world['a']}/codex/entries/{entry}"

    assert client.get(url, headers=_bearer(world["player_a"])).status_code == 200
    assert client.get(url, headers=_bearer(world["spectator_a"])).status_code == 403


@pytest.mark.asyncio
async def test_search_body_caller_id_cannot_unlock_secret_lore(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """A player who names the DM in the body is refused. The DM search returns the secret chunk."""
    await _seed_roles(spicedb, world)
    ingest = client.post(
        "/api/v1/lore/documents",
        json={
            "campaign_id": world["a"],
            "title": "Vault Record",
            "content": SECRET_TEXT,
            "is_secret": True,
        },
        headers=_bearer(world["dm_a"]),
    )
    assert ingest.status_code == 200, ingest.text

    spoofed = client.post(
        "/api/v1/lore/search",
        json={
            "campaign_id": world["a"],
            "query": "Dragon Eye gem vault",
            "caller_id": world["dm_a"],
        },
        headers=_bearer(world["player_a"]),
    )
    assert spoofed.status_code == 422, spoofed.text

    player_search = client.post(
        "/api/v1/lore/search",
        json={"campaign_id": world["a"], "query": "Dragon Eye gem vault"},
        headers=_bearer(world["player_a"]),
    )
    assert player_search.status_code == 200, player_search.text
    assert all(not item["is_secret"] for item in player_search.json()["results"])

    dm_search = client.post(
        "/api/v1/lore/search",
        json={"campaign_id": world["a"], "query": "Dragon Eye gem vault"},
        headers=_bearer(world["dm_a"]),
    )
    assert dm_search.status_code == 200, dm_search.text
    assert any(item["is_secret"] for item in dm_search.json()["results"])


@pytest.mark.asyncio
async def test_document_ingest_requires_a_dm(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """Anonymous ingest returns 401. A player ingest returns 403. A DM ingest returns 200."""
    await _seed_roles(spicedb, world)
    payload = {"campaign_id": world["a"], "title": "Gate Lore", "content": "The gate is old."}
    url = "/api/v1/lore/documents"

    assert client.post(url, json=payload).status_code == 401
    assert client.post(url, json=payload, headers=_bearer(world["player_a"])).status_code == 403
    assert client.post(url, json=payload, headers=_bearer(world["dm_a"])).status_code == 200


@pytest.mark.asyncio
async def test_atlas_layer_toggle_requires_atlas_edit(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """Anonymous toggle returns 401. A spectator or player returns 403. A DM returns 200."""
    await _seed_roles(spicedb, world)
    url = f"/api/v1/campaigns/{world['a']}/atlas/layers/toggle"
    payload = {"layer": "regional", "is_visible": True}

    assert client.post(url, json=payload).status_code == 401
    assert client.post(url, json=payload, headers=_bearer(world["spectator_a"])).status_code == 403
    assert client.post(url, json=payload, headers=_bearer(world["player_a"])).status_code == 403
    assert client.post(url, json=payload, headers=_bearer(world["dm_a"])).status_code == 200


@pytest.mark.asyncio
async def test_atlas_pin_placement_is_refused_to_spectators(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """A spectator cannot place a pin (403). A player can (201)."""
    await _seed_roles(spicedb, world)
    url = f"/api/v1/campaigns/{world['a']}/atlas/pins"
    payload = {"title": "Camp", "coordinates": {"x": 120.0, "y": 140.0}}

    spectator = client.post(url, json=payload, headers=_bearer(world["spectator_a"]))
    assert spectator.status_code == 403, spectator.text
    player = client.post(url, json=payload, headers=_bearer(world["player_a"]))
    assert player.status_code == 201, player.text


@pytest.mark.asyncio
async def test_handout_generation_requires_a_dm(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """Anonymous generate returns 401. A player generate returns 403. A DM generate returns 200."""
    await _seed_roles(spicedb, world)
    url = "/api/v1/lore/handouts/generate"
    payload = {"campaign_id": world["a"], "title": "Notice", "content": "Closed for repairs."}

    assert client.post(url, json=payload).status_code == 401
    assert client.post(url, json=payload, headers=_bearer(world["player_a"])).status_code == 403
    assert client.post(url, json=payload, headers=_bearer(world["dm_a"])).status_code == 200


@pytest.mark.asyncio
async def test_relic_forge_requires_a_dm(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """Anonymous forge returns 401. A spectator forge returns 403. A DM forge returns 200."""
    await _seed_roles(spicedb, world)
    url = "/api/v1/lore/relics/forge"
    payload = {"campaign_id": world["a"], "name": "Amulet of Ash"}

    assert client.post(url, json=payload).status_code == 401
    spectator = client.post(url, json=payload, headers=_bearer(world["spectator_a"]))
    assert spectator.status_code == 403, spectator.text
    assert client.post(url, json=payload, headers=_bearer(world["dm_a"])).status_code == 200


@pytest.mark.asyncio
async def test_west_marches_link_requires_campaign_manage(
    client: TestClient, spicedb: SpiceDBClient, world: dict[str, str]
) -> None:
    """A player cannot link the campaign to a shared world (403). The owner can (200)."""
    await _seed_roles(spicedb, world)
    await spicedb.write_relationship("campaign", world["a"], "owner", "user", world["dm_a"])
    url = f"/api/v1/campaigns/{world['a']}/west-marches/link-world"
    payload = {"shared_world_id": "frontier-1"}

    player = client.post(url, json=payload, headers=_bearer(world["player_a"]))
    assert player.status_code == 403, player.text
    owner = client.post(url, json=payload, headers=_bearer(world["dm_a"]))
    assert owner.status_code == 200, owner.text
