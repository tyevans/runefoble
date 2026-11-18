"""Blackbox tests for Audience Studio DM approval queue, SpiceDB authorization, and WebSockets.

Governed by:
- TASK-0533: verified identity; the tuple route is removed.
- TASK-0554: every action checks an audience_poll permission in the runefoble.zed schema.
- Hard Invariant 7: frontdoor setup. Roles are written into a live SpiceDB container through its
  gRPC API, as an operator would. The service is reached only through HTTP and WebSockets.
"""

from __future__ import annotations

import json
from collections.abc import Generator

import httpx
import pytest
import websockets
from websockets.exceptions import InvalidStatus

from tests.helpers.audience_server import AudienceStudioProcess, start_audience_studio_server
from tests.helpers.spicedb import LiveSpiceDB

DM = "dungeon_master"
SPECTATOR = "spectator"


@pytest.fixture(scope="module")
def audience(live_spicedb_with_schema: LiveSpiceDB) -> Generator[AudienceStudioProcess]:
    """Launch Audience Studio, pointed at the live SpiceDB container."""
    yield from start_audience_studio_server(live_spicedb_with_schema.env)


def _auth(audience: AudienceStudioProcess, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {audience.token(sub)}"}


def _setup_campaign(spicedb: LiveSpiceDB, campaign_id: str, voter: str) -> None:
    """Grants the DM that creates polls and a spectator who votes. Written into SpiceDB."""
    spicedb.grant(campaign_id, DM, "dm-setup")
    spicedb.grant(campaign_id, SPECTATOR, voter)


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


def test_dm_approval_queue_is_authorized_by_spicedb(
    audience: AudienceStudioProcess, live_spicedb_with_schema: LiveSpiceDB
):
    """A spectator cannot approve, even when the body names a DM. A granted DM approves."""
    campaign_id = "camp-auth-test"
    _setup_campaign(live_spicedb_with_schema, campaign_id, f"voter-{campaign_id}")
    live_spicedb_with_schema.grant(campaign_id, DM, "dm-gandalf")
    live_spicedb_with_schema.grant(campaign_id, SPECTATOR, "spectator-pippin")
    prop_id = _proposal_for(audience, campaign_id, "DM Moderation Test", "Blessing")

    with httpx.Client(base_url=audience.base_url) as client:
        res_denied = client.post(
            f"/api/v1/audience/proposals/{prop_id}/approve",
            headers=_auth(audience, "spectator-pippin"),
            json={"dm_user_id": "dm-gandalf"},
        )
        assert res_denied.status_code == 403

        res_auth = client.post(
            f"/api/v1/audience/proposals/{prop_id}/approve",
            headers=_auth(audience, "dm-gandalf"),
        )
        assert res_auth.status_code == 200
        prop = res_auth.json()["proposal"]
        assert prop["status"] == "approved"
        assert prop["reviewedBy"] == "dm-gandalf"


def test_dm_veto_modifier_proposal(
    audience: AudienceStudioProcess, live_spicedb_with_schema: LiveSpiceDB
):
    """An authorized DM vetoes a proposed chaos modifier."""
    campaign_id = "camp-veto"
    _setup_campaign(live_spicedb_with_schema, campaign_id, f"voter-{campaign_id}")
    live_spicedb_with_schema.grant(campaign_id, DM, "dm-merlin")
    prop_id = _proposal_for(audience, campaign_id, "Veto Test", "Lava Surge")

    with httpx.Client(base_url=audience.base_url) as client:
        res_veto = client.post(
            f"/api/v1/audience/proposals/{prop_id}/veto",
            headers=_auth(audience, "dm-merlin"),
        )
        assert res_veto.status_code == 200
        assert res_veto.json()["proposal"]["status"] == "vetoed"


def test_a_stranger_cannot_create_a_poll(audience: AudienceStudioProcess):
    """Poll creation needs run_session on the campaign. A caller with no grant is refused."""
    with httpx.Client(base_url=audience.base_url) as client:
        res = client.post(
            "/api/v1/audience/polls",
            headers=_auth(audience, "stranger-create"),
            json={"campaign_id": "camp-no-grant", "title": "T", "prompt": "P", "options": ["A"]},
        )
        assert res.status_code == 403


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
async def test_websocket_refuses_a_principal_without_campaign_view(
    audience: AudienceStudioProcess, live_spicedb_with_schema: LiveSpiceDB
):
    """A verified principal with no role on the campaign is refused before accept (403)."""
    ws_base = audience.base_url.replace("http://", "ws://")
    stranger_token = audience.token("stranger-ws")
    live_spicedb_with_schema.grant("camp-ws-private", SPECTATOR, "someone-else")
    with pytest.raises(InvalidStatus) as refused:
        async with websockets.connect(
            f"{ws_base}/ws/audience/camp-ws-private",
            subprotocols=["runefoble.v1", f"runefoble.bearer.{stranger_token}"],
        ):
            pass
    assert refused.value.response.status_code == 403


@pytest.mark.asyncio
async def test_websocket_stream_and_live_approval(
    audience: AudienceStudioProcess, live_spicedb_with_schema: LiveSpiceDB
):
    """Verify bidirectional WebSocket channel for live updates and DM action approvals."""
    ws_base = audience.base_url.replace("http://", "ws://")
    campaign_id = "camp-ws-live"
    _setup_campaign(live_spicedb_with_schema, campaign_id, f"voter-{campaign_id}")
    live_spicedb_with_schema.grant(campaign_id, DM, "dm-ws")
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
