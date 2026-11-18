"""Blackbox frontdoor tests for TASK-0552: The Watcher DM, intent, stand-in, and faction authorization.

Every request goes through a public HTTP route of The Watcher. The table setup writes only
schema relations (`campaign#dungeon_master`, `campaign#player`, `session#campaign`) through
the shared SpiceDB client. No Watcher frontdoor creates these relations yet.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization (checks use schema permissions only)
- ADR-0002: Event-Driven Watcher Gameplay Orchestration (HTTP routes are the command frontdoor)
- ADR-0014: BDD Gherkin User Stories and Playwright E2E
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.errors import AuthzSchemaError, AuthzUnavailableError
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.dependencies import set_event_bus
from the_watcher.main import app

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import make_table_runner, shared_spicedb_client
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


class _OutageSpiceDB(MockSpiceDBClient):
    """Process-boundary stub: every permission call fails as if SpiceDB were unreachable."""

    async def check_permission(self, *args, **kwargs):
        raise AuthzUnavailableError("SpiceDB stub: UNAVAILABLE")


class _DefectSpiceDB(MockSpiceDBClient):
    """Process-boundary stub: a permission name is missing from the schema."""

    async def check_permission(self, *args, **kwargs):
        raise AuthzSchemaError("SpiceDB stub: FAILED_PRECONDITION (unknown permission)")


@pytest.fixture(autouse=True)
def watcher_bus():
    set_event_bus(RedisStreamsEventBus(client=MockAsyncRedis()))
    yield
    set_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _bearer(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


async def _seed_table(dm: str, player: str) -> tuple[str, str]:
    """Create a campaign with one DM and one player, and one session in that campaign."""
    campaign_id, session_id = str(uuid4()), str(uuid4())
    await make_table_runner(dm, session_id, campaign_id)
    await get_spicedb_client().write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player,
    )
    return campaign_id, session_id


def _speech_body(session_id: str, campaign_id: str, speaker: str) -> dict:
    return {
        "speaker_id": speaker,
        "speaker_name": "Valeros",
        "transcript": "I strike the goblin with my sword",
        "session_id": session_id,
        "campaign_id": campaign_id,
    }


def test_anonymous_faction_creation_is_rejected(client: TestClient):
    """An anonymous caller gets 401. The route never returns 200 without a verified principal."""
    campaign_id = str(uuid4())
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/factions",
        json={"name": "Rogue Band", "influence": 30},
    )
    assert res.status_code == 401


def test_only_the_dm_adjusts_faction_resources(client: TestClient):
    """A player gets 403 on resource adjustment. The DM gets 200."""
    dm, player = f"dm-{uuid4().hex[:6]}", f"player-{uuid4().hex[:6]}"
    campaign_id, _ = asyncio.run(_seed_table(dm, player))
    faction_id = f"fact-{uuid4().hex[:8]}"
    body = {"treasury_delta": 100, "campaign_id": campaign_id}

    denied = client.post(
        f"/api/v1/factions/{faction_id}/resources/adjust", json=body, headers=_bearer(player)
    )
    assert denied.status_code == 403
    assert "Forbidden" in denied.json()["detail"]

    allowed = client.post(
        f"/api/v1/factions/{faction_id}/resources/adjust", json=body, headers=_bearer(dm)
    )
    assert allowed.status_code == 200
    assert allowed.json()["treasury"] == 200  # a new faction starts with 100 treasury


def test_only_the_dm_spawns_encounters(client: TestClient):
    """A player gets 403 on encounter spawn. The DM gets 200."""
    dm, player = f"dm-{uuid4().hex[:6]}", f"player-{uuid4().hex[:6]}"
    _, session_id = asyncio.run(_seed_table(dm, player))
    body = {"session_id": session_id, "party_level": 2, "party_size": 3}

    denied = client.post("/api/v1/watcher/encounters/spawn", json=body, headers=_bearer(player))
    assert denied.status_code == 403

    allowed = client.post("/api/v1/watcher/encounters/spawn", json=body, headers=_bearer(dm))
    assert allowed.status_code == 200


def test_player_speech_intent_is_allowed_for_a_participant(client: TestClient):
    """A player who participates in the campaign may send speech intent for the session."""
    dm, player = f"dm-{uuid4().hex[:6]}", f"player-{uuid4().hex[:6]}"
    campaign_id, session_id = asyncio.run(_seed_table(dm, player))

    res = client.post(
        "/api/v1/watcher/intent",
        json=_speech_body(session_id, campaign_id, speaker=player),
        headers=_bearer(player),
    )
    assert res.status_code == 200, res.text


def test_intent_from_a_non_participant_is_forbidden(client: TestClient):
    """A user with no role in the campaign gets 403 on player intent routes."""
    dm, player = f"dm-{uuid4().hex[:6]}", f"player-{uuid4().hex[:6]}"
    campaign_id, session_id = asyncio.run(_seed_table(dm, player))
    stranger = f"stranger-{uuid4().hex[:6]}"

    res = client.post(
        "/api/v1/watcher/intent",
        json=_speech_body(session_id, campaign_id, speaker=stranger),
        headers=_bearer(stranger),
    )
    assert res.status_code == 403


def test_player_cannot_veto_and_dm_can(client: TestClient):
    """A player gets a clean 403 on veto, with no schema error body. The DM veto succeeds."""
    dm, player = f"dm-{uuid4().hex[:6]}", f"player-{uuid4().hex[:6]}"
    campaign_id, session_id = asyncio.run(_seed_table(dm, player))
    proposed = client.post(
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
    action_id = proposed.json()["action_id"]
    veto_body = {
        "action_id": action_id,
        "session_id": session_id,
        "campaign_id": campaign_id,
        "reason": "Not this turn",
    }

    denied = client.post("/api/v1/watcher/veto", json=veto_body, headers=_bearer(player))
    assert denied.status_code == 403
    assert denied.json()["detail"].startswith("Forbidden")

    allowed = client.post("/api/v1/watcher/veto", json=veto_body, headers=_bearer(dm))
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "vetoed"


def test_veto_returns_503_when_spicedb_is_unavailable(client: TestClient):
    """A SpiceDB outage is 503 with a retry message. It is never a denial or an approval."""
    dm = f"dm-{uuid4().hex[:6]}"
    campaign_id, session_id = asyncio.run(_seed_table(dm, f"player-{uuid4().hex[:6]}"))

    with shared_spicedb_client(_OutageSpiceDB()):
        res = client.post(
            "/api/v1/watcher/veto",
            json={
                "action_id": "act-outage",
                "session_id": session_id,
                "campaign_id": campaign_id,
                "reason": "outage",
            },
            headers=_bearer(dm),
        )
    assert res.status_code == 503
    assert res.json()["error"] == "authorization_unavailable"


def test_schema_defect_returns_500_with_error_id(client: TestClient):
    """A name missing from the schema is a server defect. It is 500 with an error id, not 403."""
    dm = f"dm-{uuid4().hex[:6]}"
    campaign_id, session_id = asyncio.run(_seed_table(dm, f"player-{uuid4().hex[:6]}"))

    with shared_spicedb_client(_DefectSpiceDB()):
        res = client.post(
            "/api/v1/watcher/veto",
            json={
                "action_id": "act-defect",
                "session_id": session_id,
                "campaign_id": campaign_id,
                "reason": "defect",
            },
            headers=_bearer(dm),
        )
    assert res.status_code == 500
    body = res.json()
    assert body["error"] == "authorization_schema_error"
    assert len(body["error_id"]) == 32
