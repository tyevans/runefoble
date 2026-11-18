"""Set up a started game session through the public game_session HTTP frontdoor.

Blackbox gateway tests use these helpers to create the session that an MCP tool
then acts on. Every step is a public route call. No private state is written.
"""

from __future__ import annotations

from uuid import uuid4

import httpx

from tests.helpers.ws_identity import SIGNING_ISSUER


def start_session_with_player(base_url: str, dm_sub: str = "user-test") -> str:
    """Create a session, join one player, start it, and return its session id."""
    auth = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_sub)}"}
    with httpx.Client(base_url=base_url, headers=auth) as http:
        created = http.post(
            "/api/v1/sessions/create",
            json={"campaign_id": _owned_campaign(http), "title": "Ambush", "dm_id": "the_watcher"},
        )
        assert created.status_code == 200, created.text
        session_id = created.json()["session_id"]

        joined = http.post(
            f"/api/v1/sessions/{session_id}/join",
            json={
                "character_id": str(uuid4()),
                "character_name": "Valeros",
                "character_class": "Fighter",
            },
        )
        assert joined.status_code == 200, joined.text
        started = http.post(f"/api/v1/sessions/{session_id}/start")
        assert started.status_code == 200, started.text
    return str(session_id)


def _owned_campaign(client) -> str:
    """Create a campaign as the calling user, so that the caller can run sessions in it."""
    res = client.post("/api/v1/campaigns", json={"title": "Owned Campaign"})
    assert res.status_code == 201, res.text
    return res.json()["id"]
