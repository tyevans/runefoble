"""Live SpiceDB frontdoor tests for TASK-0552: The Watcher authorization.

The Watcher routes run against a real SpiceDB container with `runefoble.zed` loaded. A
schema name that the server rejects fails the test, so these tests prove the names used by
the Watcher exist in the live schema. Run with `make test-authz-live` (needs Docker).

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from the_watcher.main import app

from tests.helpers.spicedb_factory import make_table_runner, shared_spicedb_client
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = [pytest.mark.authz_live, pytest.mark.usefixtures("trusted_ws_issuer")]


@pytest.fixture
def live_client(live_spicedb_with_schema):
    """The Watcher shares the live SpiceDB client for the duration of one test."""
    with shared_spicedb_client(live_spicedb_with_schema.client):
        yield TestClient(app)


def _bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def test_live_dm_and_player_roles_gate_encounter_spawn(live_client: TestClient):
    """On live SpiceDB, the DM spawns an encounter and the player gets 403."""
    dm, player = f"dm-{uuid4().hex[:6]}", f"player-{uuid4().hex[:6]}"
    campaign_id, session_id = str(uuid4()), str(uuid4())

    async def _seed() -> None:
        from runefoble_auth.factory import get_spicedb_client

        await make_table_runner(dm, session_id, campaign_id)
        await get_spicedb_client().write_relationship(
            resource_type="campaign",
            resource_id=campaign_id,
            relation="player",
            subject_type="user",
            subject_id=player,
        )

    asyncio.run(_seed())
    body = {"session_id": session_id, "party_level": 2, "party_size": 3}

    denied = live_client.post(
        "/api/v1/watcher/encounters/spawn", json=body, headers=_bearer(player)
    )
    assert denied.status_code == 403

    allowed = live_client.post("/api/v1/watcher/encounters/spawn", json=body, headers=_bearer(dm))
    assert allowed.status_code == 200


def test_live_player_cannot_veto_and_dm_can(live_client: TestClient):
    """On live SpiceDB, a player veto is 403 and the DM veto is 200."""
    dm, player = f"dm-{uuid4().hex[:6]}", f"player-{uuid4().hex[:6]}"
    campaign_id, session_id = str(uuid4()), str(uuid4())

    async def _seed() -> None:
        from runefoble_auth.factory import get_spicedb_client

        await make_table_runner(dm, session_id, campaign_id)
        await get_spicedb_client().write_relationship(
            resource_type="campaign",
            resource_id=campaign_id,
            relation="player",
            subject_type="user",
            subject_id=player,
        )

    asyncio.run(_seed())
    proposed = live_client.post(
        "/api/v1/watcher/actions/propose",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "actor_name": "Goblin",
            "action_type": "attack",
            "description": "Attacks target",
            "pause_window_ms": 60000,
        },
        headers=_bearer(dm),
    )
    assert proposed.status_code == 200, proposed.text
    veto_body = {
        "action_id": proposed.json()["action_id"],
        "session_id": session_id,
        "campaign_id": campaign_id,
        "reason": "Not this turn",
    }

    denied = live_client.post("/api/v1/watcher/veto", json=veto_body, headers=_bearer(player))
    assert denied.status_code == 403

    allowed = live_client.post("/api/v1/watcher/veto", json=veto_body, headers=_bearer(dm))
    assert allowed.status_code == 200
