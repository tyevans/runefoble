"""Blackbox tests: one id per session from the campaign list to the game session aggregate.

TASK-0706. A campaign session creates the GameSession aggregate in the same call. The id
the campaign returns is the aggregate UUID, and the session read, start, and combat routes
accept it. Setup uses public frontdoors only (ADR-0014, Hard Invariant 7).
"""

from collections.abc import Iterator
from uuid import UUID

import pytest
import pytest_asyncio
from game_session.main import app as session_app
from httpx import ASGITransport, AsyncClient
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM, PLAYER = "dm-one-id", "player-one-id"


@pytest.fixture
def spicedb() -> Iterator[None]:
    with shared_spicedb_client(MockSpiceDBClient()):
        yield


@pytest_asyncio.fixture
async def client(spicedb) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=session_app), base_url="http://test"
    ) as http:
        yield http


@pytest_asyncio.fixture
async def campaign_id(client: AsyncClient) -> str:
    res = await client.post("/api/v1/campaigns", json={"title": "One Id"}, headers=bearer(DM))
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.mark.asyncio
async def test_created_campaign_session_id_is_the_game_session_uuid(client, campaign_id):
    res = await client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Session #2"},
        headers=bearer(DM),
    )
    assert res.status_code == 201, res.text
    session_id = res.json()["id"]
    assert str(UUID(session_id)) == session_id

    state = await client.get(f"/api/v1/sessions/{session_id}", headers=bearer(DM))
    assert state.status_code == 200, state.text
    assert state.json()["session_id"] == session_id
    assert state.json()["campaign_id"] == campaign_id
    assert state.json()["status"] == "lobby"


@pytest.mark.asyncio
async def test_the_same_id_starts_combats_and_advances_turns(client, campaign_id):
    created = await client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Session #3"},
        headers=bearer(DM),
    )
    session_id = created.json()["id"]

    started = await client.post(f"/api/v1/sessions/{session_id}/start", headers=bearer(DM))
    assert started.status_code == 200, started.text
    combat = await client.post(
        f"/api/v1/sessions/{session_id}/combat/start",
        json={"combatants": []},
        headers=bearer(DM),
    )
    assert combat.status_code == 200, combat.text
    assert combat.json()["session_id"] == session_id
    initiative = await client.post(
        f"/api/v1/sessions/{session_id}/combat/initiative",
        json={"combatant_id": "c1", "combatant_name": "Orc", "initiative_score": 12},
        headers=bearer(DM),
    )
    assert initiative.status_code == 200, initiative.text
    advanced = await client.post(
        f"/api/v1/sessions/{session_id}/combat/next-turn", headers=bearer(DM)
    )
    assert advanced.status_code == 200, advanced.text


@pytest.mark.asyncio
async def test_campaign_list_and_seeded_session_use_the_aggregate_id(client, campaign_id):
    listed = await client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=bearer(DM))
    assert listed.status_code == 200, listed.text
    seeded = listed.json()
    assert len(seeded) == 1
    seeded_id = seeded[0]["id"]
    assert str(UUID(seeded_id)) == seeded_id

    state = await client.get(f"/api/v1/sessions/{seeded_id}", headers=bearer(DM))
    assert state.status_code == 200, state.text
    assert state.json()["session_id"] == seeded_id


@pytest.mark.asyncio
async def test_a_player_reads_the_session_by_the_listed_id(client, campaign_id):
    invite = await client.post(
        f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"}, headers=bearer(DM)
    )
    joined = await client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(PLAYER),
    )
    assert joined.status_code == 200, joined.text
    listed = await client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=bearer(PLAYER))
    session_id = listed.json()[0]["id"]
    state = await client.get(f"/api/v1/sessions/{session_id}", headers=bearer(PLAYER))
    assert state.status_code == 200, state.text
