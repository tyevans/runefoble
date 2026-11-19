"""Blackbox tests: session lifecycle routes act for the verified caller (TASK-0767).

Setup uses public frontdoors only: campaign create, invite redeem, session create.
Each check reads session state through the public GET route.
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
import pytest_asyncio
from game_session.main import app as session_app
from httpx import ASGITransport, AsyncClient
from runefoble_auth.factory import set_spicedb_client
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.ws_identity import bearer

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM, PLAYER, OTHER, STRANGER = "dm-user", "player-user", "other-user", "stranger-user"


def _seat() -> dict[str, str]:
    return {"character_id": str(uuid4()), "character_name": "Kyra", "character_class": "Cleric"}


@pytest.fixture
def spicedb() -> Iterator[None]:
    set_spicedb_client(MockSpiceDBClient())
    yield


@pytest_asyncio.fixture
async def client(spicedb) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=session_app), base_url="http://test"
    ) as http:
        yield http


@pytest_asyncio.fixture
async def session_id(client: AsyncClient) -> str:
    """The DM runs a campaign with two players, then creates a session in it."""
    campaign = await client.post("/api/v1/campaigns", json={"title": "Lobby"}, headers=bearer(DM))
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    for user in (PLAYER, OTHER):
        invite = await client.post(
            f"/api/v1/campaigns/{campaign_id}/invites", json={"role": "player"}, headers=bearer(DM)
        )
        joined = await client.post(
            "/api/v1/campaigns/join",
            json={"invite_token": invite.json()["token"]},
            headers=bearer(user),
        )
        assert joined.status_code == 200, joined.text
    created = await client.post(
        "/api/v1/sessions/create", json={"campaign_id": campaign_id}, headers=bearer(DM)
    )
    assert created.status_code == 200, created.text
    return created.json()["session_id"]


async def _state(client: AsyncClient, session_id: str) -> dict:
    res = await client.get(f"/api/v1/sessions/{session_id}", headers=bearer(DM))
    assert res.status_code == 200, res.text
    return res.json()


@pytest.mark.asyncio
async def test_player_joins_readies_and_leaves_their_own_seat(client, session_id):
    base = f"/api/v1/sessions/{session_id}"
    joined = await client.post(f"{base}/join", json=_seat(), headers=bearer(PLAYER))
    assert joined.status_code == 200, joined.text
    assert list(joined.json()["participants"]) == [PLAYER]
    ready = await client.post(
        f"{base}/lobby/readiness", json={"is_ready": True}, headers=bearer(PLAYER)
    )
    assert ready.status_code == 200, ready.text
    assert ready.json()["lobby_readiness"] == {PLAYER: True}
    left = await client.post(f"{base}/leave", json={"reason": "bed"}, headers=bearer(PLAYER))
    assert left.status_code == 200, left.text
    assert left.json()["participants"][PLAYER]["is_present"] is False


@pytest.mark.asyncio
async def test_body_player_id_cannot_act_for_another_player(client, session_id):
    """A player id in the body is ignored. The seat is the caller's, never the named player's."""
    base = f"/api/v1/sessions/{session_id}"
    forged = {**_seat(), "player_id": OTHER}
    joined = await client.post(f"{base}/join", json=forged, headers=bearer(PLAYER))
    assert joined.status_code == 200, joined.text
    assert list(joined.json()["participants"]) == [PLAYER]
    state = await _state(client, session_id)
    assert OTHER not in state["participants"]
    assert state["lobby_readiness"] == {}


@pytest.mark.asyncio
async def test_user_without_campaign_relation_is_refused_on_every_route(client, session_id):
    base = f"/api/v1/sessions/{session_id}"
    attempts = [
        ("start", {}),
        ("join", _seat()),
        ("leave", {"reason": "x"}),
        ("lobby/readiness", {"is_ready": True}),
        ("lobby/character", {"character_id": str(uuid4())}),
    ]
    for route, body in attempts:
        res = await client.post(f"{base}/{route}", json=body, headers=bearer(STRANGER))
        assert res.status_code == 403, f"{route}: {res.status_code} {res.text}"
    state = await _state(client, session_id)
    assert state["status"] == "lobby"
    assert state["participants"] == {}


@pytest.mark.asyncio
async def test_only_the_dm_starts_the_session(client, session_id):
    base = f"/api/v1/sessions/{session_id}"
    refused = await client.post(f"{base}/start", headers=bearer(PLAYER))
    assert refused.status_code == 403, refused.text
    assert (await _state(client, session_id))["status"] == "lobby"
    started = await client.post(f"{base}/start", headers=bearer(DM))
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "active"
