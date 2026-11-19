"""Set up campaigns, sessions and party members through the public game_session routes.

Blackbox tests call these helpers to reach a known state before they assert behaviour.
Every step is a public HTTP call with a signed bearer token. No helper writes SpiceDB,
the event store or any repository.

Governed by ADR-0001, ADR-0014 and Hard Invariant 7.
"""

from __future__ import annotations

from uuid import uuid4

import httpx

from tests.helpers.ws_identity import bearer


def create_campaign(client: httpx.Client, owner_id: str, title: str | None = None) -> str:
    """Create a campaign as `owner_id` through `POST /api/v1/campaigns` and return its id."""
    res = client.post(
        "/api/v1/campaigns",
        json={"title": title or f"Campaign {uuid4().hex[:8]}"},
        headers=bearer(owner_id),
    )
    assert res.status_code == 201, res.text
    return str(res.json()["id"])


def create_campaign_session(client: httpx.Client, owner_id: str) -> tuple[str, str]:
    """Create a campaign as `owner_id` and return (campaign_id, first_session_id).

    The campaign route creates the first session. The session list route returns it.
    """
    campaign_id = create_campaign(client, owner_id)
    sessions = client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=bearer(owner_id))
    assert sessions.status_code == 200, sessions.text
    return campaign_id, str(sessions.json()[0]["id"])


def invite_and_join(
    client: httpx.Client,
    campaign_id: str,
    owner_id: str,
    member_id: str,
    role: str = "player",
) -> None:
    """Owner issues an invite for `role`; `member_id` redeems it through the public join route."""
    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": role},
        headers=bearer(owner_id),
    )
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join",
        json={"invite_token": invite.json()["token"]},
        headers=bearer(member_id),
    )
    assert joined.status_code == 200, joined.text
