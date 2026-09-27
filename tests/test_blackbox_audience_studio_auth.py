"""Blackbox tests for Audience Studio DM approval queue, SpiceDB auth, and WebSockets."""

from __future__ import annotations

import json
from collections.abc import Generator

import httpx
import pytest
import websockets

from tests.helpers.audience_server import start_audience_studio_server


@pytest.fixture(scope="module")
def audience_url() -> Generator[str]:
    """Launch Audience Studio Fastify server as an isolated subprocess."""
    yield from start_audience_studio_server()


def test_dm_approval_queue_and_zanzibar_auth(audience_url: str):
    """Verify DM approval queue requires dungeon_master permission via Zanzibar."""
    with httpx.Client(base_url=audience_url) as client:
        campaign_id = "camp-auth-test"

        # Setup SpiceDB Zanzibar relationship tuples
        client.post(
            "/api/v1/audience/auth/tuples",
            json={
                "resource_type": "campaign",
                "resource_id": campaign_id,
                "relation": "dungeon_master",
                "subject_type": "user",
                "subject_id": "dm-gandalf",
            },
        )
        client.post(
            "/api/v1/audience/auth/tuples",
            json={
                "resource_type": "campaign",
                "resource_id": campaign_id,
                "relation": "spectator",
                "subject_type": "user",
                "subject_id": "spectator-pippin",
            },
        )

        # Create poll and vote to generate proposal
        poll = client.post(
            "/api/v1/audience/polls",
            json={
                "campaign_id": campaign_id,
                "title": "DM Moderation Test",
                "prompt": "Test modifier proposal",
                "options": ["Blessing", "Curse"],
                "quorum": 1,
            },
        ).json()
        client.post(
            f"/api/v1/audience/polls/{poll['id']}/votes",
            json={"voter_id": "voter-a", "option_id": "opt_1"},
        )
        closed = client.post(f"/api/v1/audience/polls/{poll['id']}/close").json()
        prop_id = closed["proposedModifier"]["id"]

        # Non-DM user (spectator) cannot approve modifier (403 Forbidden)
        res_unauth = client.post(
            f"/api/v1/audience/proposals/{prop_id}/approve",
            json={"dm_user_id": "spectator-pippin"},
        )
        assert res_unauth.status_code == 403
        assert "dungeon_master" in res_unauth.json()["error"]

        # Authorized DM approves modifier
        res_auth = client.post(
            f"/api/v1/audience/proposals/{prop_id}/approve",
            json={"dm_user_id": "dm-gandalf"},
        )
        assert res_auth.status_code == 200
        prop = res_auth.json()["proposal"]
        assert prop["status"] == "approved"
        assert prop["reviewedBy"] == "dm-gandalf"


def test_dm_veto_modifier_proposal(audience_url: str):
    """Verify authorized DM can veto a proposed chaos modifier."""
    with httpx.Client(base_url=audience_url) as client:
        campaign_id = "camp-veto"
        client.post(
            "/api/v1/audience/auth/tuples",
            json={
                "resource_type": "campaign",
                "resource_id": campaign_id,
                "relation": "dungeon_master",
                "subject_type": "user",
                "subject_id": "dm-merlin",
            },
        )

        poll = client.post(
            "/api/v1/audience/polls",
            json={
                "campaign_id": campaign_id,
                "title": "Veto Test",
                "prompt": "Dangerous hazard",
                "options": ["Lava Surge"],
                "quorum": 1,
            },
        ).json()
        client.post(
            f"/api/v1/audience/polls/{poll['id']}/votes",
            json={"voter_id": "voter-b", "option_id": "opt_1"},
        )
        closed = client.post(f"/api/v1/audience/polls/{poll['id']}/close").json()
        prop_id = closed["proposedModifier"]["id"]

        res_veto = client.post(
            f"/api/v1/audience/proposals/{prop_id}/veto",
            json={"dm_user_id": "dm-merlin"},
        )
        assert res_veto.status_code == 200
        assert res_veto.json()["proposal"]["status"] == "vetoed"


@pytest.mark.asyncio
async def test_websocket_stream_and_live_approval(audience_url: str):
    """Verify bidirectional WebSocket channel for live updates and DM action approvals."""
    ws_base = audience_url.replace("http://", "ws://")
    campaign_id = "camp-ws-live"

    # Register DM relationship
    async with httpx.AsyncClient(base_url=audience_url) as client:
        await client.post(
            "/api/v1/audience/auth/tuples",
            json={
                "resource_type": "campaign",
                "resource_id": campaign_id,
                "relation": "dungeon_master",
                "subject_type": "user",
                "subject_id": "dm-ws",
            },
        )
        poll = (
            await client.post(
                "/api/v1/audience/polls",
                json={
                    "campaign_id": campaign_id,
                    "title": "WS Poll",
                    "prompt": "WS Test Prompt",
                    "options": ["Opt A"],
                    "quorum": 1,
                },
            )
        ).json()
        await client.post(
            f"/api/v1/audience/polls/{poll['id']}/votes",
            json={"voter_id": "voter-ws", "option_id": "opt_1"},
        )
        closed = (await client.post(f"/api/v1/audience/polls/{poll['id']}/close")).json()
        prop_id = closed["proposedModifier"]["id"]

    # Connect to WebSocket
    async with websockets.connect(f"{ws_base}/ws/audience/{campaign_id}") as ws:
        connected_raw = await ws.recv()
        connected_msg = json.loads(connected_raw)
        assert connected_msg["type"] == "connected"

        # Subscribe
        await ws.send(
            json.dumps({"action": "subscribe", "userId": "dm-ws", "role": "dungeon_master"})
        )
        sub_msg = json.loads(await ws.recv())
        assert sub_msg["type"] == "subscribed"

        # Approve proposal over WebSocket
        await ws.send(
            json.dumps({"action": "approve_proposal", "proposalId": prop_id, "userId": "dm-ws"})
        )
        resp_msg = json.loads(await ws.recv())
        assert resp_msg["type"] in ("proposal_approved", "proposal_queued")
