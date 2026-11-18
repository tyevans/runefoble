"""Blackbox tests: combat, dice, turn, reaction, and autopilot routes check session permissions.

Setup uses public frontdoors only: campaign create, invite redeem, session create, session start.
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
import pytest_asyncio
from game_session.main import app as session_app
from game_session.main import set_spicedb_client as session_set_spicedb
from httpx import ASGITransport, AsyncClient
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

DM, PLAYER, SPECTATOR, STRANGER = "dm-user", "player-user", "spectator-user", "stranger-user"


def _bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def spicedb() -> Iterator[None]:
    session_set_spicedb(MockSpiceDBClient())
    yield


@pytest_asyncio.fixture
async def client(spicedb) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=session_app), base_url="http://test"
    ) as http:
        yield http


@pytest_asyncio.fixture
async def session_id(client: AsyncClient) -> str:
    campaign = await client.post("/api/v1/campaigns", json={"title": "War"}, headers=_bearer(DM))
    campaign_id = campaign.json()["id"]
    for user, role in ((PLAYER, "player"), (SPECTATOR, "spectator")):
        invite = await client.post(
            f"/api/v1/campaigns/{campaign_id}/invites", json={"role": role}, headers=_bearer(DM)
        )
        joined = await client.post(
            "/api/v1/campaigns/join",
            json={"invite_token": invite.json()["token"]},
            headers=_bearer(user),
        )
        assert joined.status_code == 200, joined.text
    created = await client.post(
        "/api/v1/sessions/create", json={"campaign_id": campaign_id}, headers=_bearer(DM)
    )
    sid = created.json()["session_id"]
    started = await client.post(f"/api/v1/sessions/{sid}/start", headers=_bearer(DM))
    assert started.status_code == 200, started.text
    return sid


CONTROL_ROUTES = [
    ("combat/start", {"combatants": []}),
    ("combat/initiative", {"combatant_id": "c1", "combatant_name": "Orc", "initiative_score": 12}),
    ("combat/next-turn", {}),
    ("combat/end", {}),
    ("next-turn", {}),
    ("autopilot", {}),
    ("reactions/evaluate-triggers", {"event_type": "x"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("route", "body"), CONTROL_ROUTES)
async def test_control_routes_refuse_players_and_anonymous_callers(client, session_id, route, body):
    url = f"/api/v1/sessions/{session_id}/{route}"
    assert (await client.post(url, json=body)).status_code == 401
    for user in (PLAYER, SPECTATOR, STRANGER):
        res = await client.post(url, json=body, headers=_bearer(user))
        assert res.status_code == 403, f"{route} as {user}: {res.status_code}"
    state = (await client.get(f"/api/v1/sessions/{session_id}", headers=_bearer(DM))).json()
    assert state["in_combat"] is False


@pytest.mark.asyncio
async def test_dm_starts_combat_and_a_player_cannot_end_it(client, session_id):
    base = f"/api/v1/sessions/{session_id}/combat"
    started = await client.post(f"{base}/start", json={"combatants": []}, headers=_bearer(DM))
    assert started.status_code == 200, started.text
    assert (await client.post(f"{base}/end", headers=_bearer(PLAYER))).status_code == 403
    state = (await client.get(f"/api/v1/sessions/{session_id}", headers=_bearer(DM))).json()
    assert state["in_combat"] is True


@pytest.mark.asyncio
async def test_roll_is_recorded_for_the_verified_roller(client, session_id):
    url = f"/api/v1/sessions/{session_id}/roll"
    res = await client.post(
        url, json={"formula": "1d20", "roller_id": "someone-else"}, headers=_bearer(PLAYER)
    )
    assert res.status_code == 200, res.text
    assert res.json()["roller_id"] == PLAYER
    assert (await client.post(url, json={}, headers=_bearer(SPECTATOR))).status_code == 403
    assert (await client.post(url, json={}, headers=_bearer(STRANGER))).status_code == 403


@pytest.mark.asyncio
async def test_reaction_routes_need_participation_and_observation(client, session_id):
    base = f"/api/v1/sessions/{session_id}/reactions"
    declare = {"reacting_combatant_id": "c1", "trigger_phrase": "Shield!"}
    ready = {"combatant_id": "c1", "trigger_condition": "enemy near", "readied_action": "strike"}
    for route, body in (("declare", declare), ("ready-action", ready), (f"{uuid4()}/resolve", {})):
        for user in (SPECTATOR, STRANGER):
            res = await client.post(f"{base}/{route}", json=body, headers=_bearer(user))
            assert res.status_code == 403, f"{route} as {user}"
    # The player passes the check. The session is not in combat, so the route answers 400.
    res = await client.post(f"{base}/declare", json=declare, headers=_bearer(PLAYER))
    assert res.status_code == 400, res.text
    assert (await client.get(f"{base}/active", headers=_bearer(SPECTATOR))).status_code == 200
    assert (await client.get(f"{base}/active", headers=_bearer(STRANGER))).status_code == 403
