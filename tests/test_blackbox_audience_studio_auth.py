"""Blackbox tests for Audience Studio DM approval queue, SpiceDB auth, and WebSockets.

Governed by TASK-0533 (verified identity; the tuple route is removed) and Hard Invariant 7.
The DM role is granted through SpiceDB's own write route, not through the service.
"""

from __future__ import annotations

import json
from collections.abc import Generator

import httpx
import pytest
import websockets
from websockets.exceptions import InvalidStatus

from tests.helpers.audience_server import AudienceStudioProcess
from tests.helpers.fake_spicedb import FakeSpiceDB


@pytest.fixture(scope="module")
def spicedb() -> Generator[FakeSpiceDB]:
    fake = FakeSpiceDB()
    try:
        yield fake
    finally:
        fake.stop()


@pytest.fixture(scope="module")
def audience(spicedb: FakeSpiceDB) -> Generator[AudienceStudioProcess]:
    """Launch Audience Studio as a subprocess that checks permissions against the fake SpiceDB."""
    process = AudienceStudioProcess({"RUNEFOBLE_SPICEDB_ENDPOINT": spicedb.url})
    process.start()
    try:
        yield process
    finally:
        process.stop()


def _auth(audience: AudienceStudioProcess, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {audience.token(sub)}"}


def _proposal_for(
    audience: AudienceStudioProcess, campaign_id: str, title: str, option: str
) -> str:
    """Create a poll, cast one vote, and close it. Returns the pending proposal id."""
    with httpx.Client(base_url=audience.base_url) as client:
        poll = client.post(
            "/api/v1/audience/polls",
            headers=_auth(audience, "dm-setup"),
            json={
                "campaign_id": campaign_id,
                "title": title,
                "prompt": "Test modifier proposal",
                "options": [option],
                "quorum": 1,
            },
        ).json()
        client.post(
            f"/api/v1/audience/polls/{poll['id']}/votes",
            headers=_auth(audience, f"voter-{campaign_id}"),
            json={"option_id": "opt_1"},
        )
        closed = client.post(
            f"/api/v1/audience/polls/{poll['id']}/close",
            headers=_auth(audience, "dm-setup"),
        ).json()
        return closed["proposedModifier"]["id"]


def test_dm_approval_queue_and_zanzibar_auth(audience: AudienceStudioProcess, spicedb: FakeSpiceDB):
    """Verify DM approval queue requires dungeon_master permission via Zanzibar."""
    campaign_id = "camp-auth-test"
    spicedb.grant(campaign_id, "dungeon_master", "dm-gandalf")
    prop_id = _proposal_for(audience, campaign_id, "DM Moderation Test", "Blessing")

    with httpx.Client(base_url=audience.base_url) as client:
        # A spectator token cannot approve, even when the body names a DM.
        res_unauth = client.post(
            f"/api/v1/audience/proposals/{prop_id}/approve",
            headers=_auth(audience, "spectator-pippin"),
            json={"dm_user_id": "dm-gandalf"},
        )
        assert res_unauth.status_code == 403
        assert "dungeon_master" in res_unauth.json()["error"]

        # The token subject is the actor. An authorized DM approves.
        res_auth = client.post(
            f"/api/v1/audience/proposals/{prop_id}/approve",
            headers=_auth(audience, "dm-gandalf"),
        )
        assert res_auth.status_code == 200
        prop = res_auth.json()["proposal"]
        assert prop["status"] == "approved"
        assert prop["reviewedBy"] == "dm-gandalf"


def test_dm_veto_modifier_proposal(audience: AudienceStudioProcess, spicedb: FakeSpiceDB):
    """Verify authorized DM can veto a proposed chaos modifier."""
    campaign_id = "camp-veto"
    spicedb.grant(campaign_id, "dungeon_master", "dm-merlin")
    prop_id = _proposal_for(audience, campaign_id, "Veto Test", "Lava Surge")

    with httpx.Client(base_url=audience.base_url) as client:
        res_veto = client.post(
            f"/api/v1/audience/proposals/{prop_id}/veto",
            headers=_auth(audience, "dm-merlin"),
        )
        assert res_veto.status_code == 200
        assert res_veto.json()["proposal"]["status"] == "vetoed"


@pytest.mark.asyncio
async def test_websocket_refuses_a_handshake_without_a_bearer_subprotocol(
    audience: AudienceStudioProcess,
):
    """Verify the handshake is refused before accept when no verified token is offered."""
    ws_base = audience.base_url.replace("http://", "ws://")
    with pytest.raises(InvalidStatus) as refused:
        async with websockets.connect(
            f"{ws_base}/ws/audience/camp-ws-anon", subprotocols=["runefoble.v1"]
        ):
            pass
    assert refused.value.response.status_code == 401


@pytest.mark.asyncio
async def test_websocket_stream_and_live_approval(
    audience: AudienceStudioProcess, spicedb: FakeSpiceDB
):
    """Verify bidirectional WebSocket channel for live updates and DM action approvals."""
    ws_base = audience.base_url.replace("http://", "ws://")
    campaign_id = "camp-ws-live"
    spicedb.grant(campaign_id, "dungeon_master", "dm-ws")
    prop_id = _proposal_for(audience, campaign_id, "WS Poll", "Opt A")

    # The DM token travels in the bearer subprotocol. The server accepts runefoble.v1 only.
    dm_token = audience.token("dm-ws")
    async with websockets.connect(
        f"{ws_base}/ws/audience/{campaign_id}",
        subprotocols=["runefoble.v1", f"runefoble.bearer.{dm_token}"],
    ) as ws:
        assert ws.subprotocol == "runefoble.v1"
        connected_msg = json.loads(await ws.recv())
        assert connected_msg["type"] == "connected"

        await ws.send(json.dumps({"action": "subscribe"}))
        sub_msg = json.loads(await ws.recv())
        assert sub_msg["type"] == "subscribed"
        assert sub_msg["data"]["userId"] == "dm-ws"

        # Approve over WebSocket. The actor is the handshake principal, not a message field.
        await ws.send(
            json.dumps({"action": "approve_proposal", "proposalId": prop_id, "userId": "spectator"})
        )
        resp_msg = json.loads(await ws.recv())
        assert resp_msg["type"] == "proposal_approved"
        assert resp_msg["data"]["reviewedBy"] == "dm-ws"
