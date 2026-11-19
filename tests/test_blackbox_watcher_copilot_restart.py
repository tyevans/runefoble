"""Blackbox restart tests for DM pending actions, whispers, and disambiguations (TASK-0568).

Governed by:
- Hard Invariant 2: domain state changes flow through DeclarativeAggregate subclasses
- Hard Invariant 7: blackbox TDD with frontdoor setup

A restart discards the copilot engine and its timers. The event store survives, as it
does in a real deployment. Tests touch only public HTTP routes, the watcher stream, and
a new app over the same store. They never read or write private aggregate state.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from eventsource.adapters.memory.store import InMemoryEventStore
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from runefoble_auth.factory import get_spicedb_client

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.spicedb_factory import bind_session_to_campaign, make_table_runner
from tests.helpers.the_watcher_app import app_with_container, container_over, repositories_over
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def _headers(user: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(user)}"}


def _listed_status(
    app: FastAPI, sess_id: str, camp_id: str, user: str, action_id: str, status: str
) -> bool:
    """Return True when the pending list shows the action with the given status."""
    res = TestClient(app).get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers=_headers(user),
    )
    return res.status_code == 200 and any(
        a["action_id"] == action_id and a["status"] == status for a in res.json()
    )


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


class WatcherProcess:
    """One Watcher process over an event store that survives restarts."""

    def __init__(self) -> None:
        self.repositories = repositories_over(InMemoryEventStore())
        self.app = self._boot()

    def _boot(self) -> FastAPI:
        return app_with_container(container_over(self.repositories))

    def restart(self) -> None:
        """Stop the running engine (its timers die with the process) and start a new app."""
        self.app.state.container.copilot.shutdown()
        self.app = self._boot()


@pytest.fixture(autouse=True)
def redis_double(use_redis_client, mock_redis: MockAsyncRedis) -> None:
    use_redis_client(mock_redis)


@pytest.fixture
def process() -> Iterator[WatcherProcess]:
    """Give each test one event store that survives restarts. Teardown stops the last engine."""
    watcher = WatcherProcess()
    yield watcher
    watcher.app.state.container.copilot.shutdown()


async def _setup_dm(dm_user: str) -> tuple[str, str]:
    camp_id, sess_id = str(uuid4()), str(uuid4())
    await get_spicedb_client().write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )
    await bind_session_to_campaign(sess_id, camp_id)
    return camp_id, sess_id


def _propose(client: TestClient, sess_id: str, camp_id: str, dm: str, **kwargs: Any) -> str:
    body = {
        "session_id": sess_id,
        "campaign_id": camp_id,
        "actor_name": "Goblin",
        "action_type": "attack",
        "description": "Attacks target",
        **kwargs,
    }
    res = client.post("/api/v1/watcher/actions/propose", json=body, headers=_headers(dm))
    assert res.status_code == 200, res.text
    return res.json()["action_id"]


@pytest.mark.asyncio
async def test_pending_action_survives_restart_and_is_vetoed_by_dm(
    process: WatcherProcess, mock_redis: MockAsyncRedis
):
    """Propose, restart, then veto through HTTP. The pending list then shows the veto."""
    dm = f"dm-{uuid4().hex[:6]}"
    camp_id, sess_id = await _setup_dm(dm)
    client = TestClient(process.app)
    action_id = _propose(client, sess_id, camp_id, dm, pause_window_ms=60000)

    process.restart()
    client = TestClient(process.app)

    listed = client.get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers=_headers(dm),
    )
    assert listed.status_code == 200, listed.text
    assert [a["status"] for a in listed.json() if a["action_id"] == action_id] == ["pending"]

    veto = client.post(
        "/api/v1/watcher/veto",
        json={
            "action_id": action_id,
            "session_id": sess_id,
            "campaign_id": camp_id,
            "reason": "Restart check",
        },
        headers=_headers(dm),
    )
    assert veto.status_code == 200, veto.text
    assert veto.json()["status"] == "vetoed"

    after = client.get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers=_headers(dm),
    )
    assert after.status_code == 200, after.text
    vetoed = [a for a in after.json() if a["action_id"] == action_id]
    assert [a["status"] for a in vetoed] == ["vetoed"]
    assert vetoed[0]["actor_name"] == "Goblin"


@pytest.mark.asyncio
async def test_unknown_action_veto_is_not_found(
    process: WatcherProcess, mock_redis: MockAsyncRedis
):
    """A veto for an action that no session holds returns 404. It never creates a phantom."""
    dm = f"dm-{uuid4().hex[:6]}"
    camp_id, sess_id = await _setup_dm(dm)
    client = TestClient(process.app)

    res = client.post(
        "/api/v1/watcher/veto",
        json={
            "action_id": f"act-{uuid4().hex[:8]}",
            "session_id": sess_id,
            "campaign_id": camp_id,
            "reason": "No such action",
        },
        headers=_headers(dm),
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_pending_action_expires_after_restart_without_dm_decision(
    process: WatcherProcess,
    mock_redis: MockAsyncRedis,
):
    """An action with a 1-second window expires after a restart. The pending list shows it.

    The lifespan re-arms timers from the stored deadline. The timer that propose started
    belonged to the previous process, so only the restart can expire this action.
    """
    dm = f"dm-{uuid4().hex[:6]}"
    camp_id, sess_id = await _setup_dm(dm)
    action_id = _propose(TestClient(process.app), sess_id, camp_id, dm, pause_window_ms=1000)

    process.restart()
    with TestClient(process.app, headers=_headers(dm)):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and not _listed_status(
            process.app, sess_id, camp_id, dm, action_id, "executed"
        ):
            time.sleep(0.1)

    assert _listed_status(process.app, sess_id, camp_id, dm, action_id, "executed")


@pytest.mark.asyncio
async def test_open_disambiguation_survives_restart_and_resolves(
    process: WatcherProcess,
    mock_redis: MockAsyncRedis,
):
    """Open a disambiguation, restart, then resolve it. A second resolve finds nothing."""
    s_id, c_id = str(uuid4()), str(uuid4())
    entities = [
        {
            "id": "goblin_1",
            "name": "Goblin",
            "tag": "archer",
            "descriptor": "archer by the pillar",
            "x": 5,
            "y": 3,
            "hp": 7,
            "is_friendly": False,
        },
        {
            "id": "goblin_2",
            "name": "Goblin",
            "tag": "shaman",
            "descriptor": "shaman on the altar",
            "x": 8,
            "y": 9,
            "hp": 12,
            "is_friendly": False,
        },
    ]
    await make_table_runner("test-user", s_id, c_id)
    async with AsyncClient(
        transport=ASGITransport(app=process.app),
        base_url="http://test",
        headers=_headers("test-user"),
    ) as client:
        parse = await client.post(
            "/api/v1/watcher/intent/parse",
            json={
                "speaker_id": "marcus-1",
                "speaker_name": "Marcus",
                "transcript": "I shoot the goblin",
                "session_id": s_id,
                "campaign_id": c_id,
                "entities": entities,
                "from_x": 1,
                "from_y": 1,
            },
        )
        assert parse.status_code == 200, parse.text
        d_id = parse.json()["disambiguation_id"]
        assert d_id

    process.restart()

    resolve_body = {
        "session_id": s_id,
        "campaign_id": c_id,
        "disambiguation_id": d_id,
        "selected_candidate_id": "goblin_2",
    }
    async with AsyncClient(
        transport=ASGITransport(app=process.app),
        base_url="http://test",
        headers=_headers("test-user"),
    ) as client:
        resolved = await client.post("/api/v1/watcher/intent/resolve", json=resolve_body)
        assert resolved.status_code == 200, resolved.text
        assert "shaman on the altar" in resolved.json()["resolved_target"]

        again = await client.post("/api/v1/watcher/intent/resolve", json=resolve_body)
        assert again.status_code == 404


@pytest.mark.asyncio
async def test_whispers_survive_restart(process: WatcherProcess, mock_redis: MockAsyncRedis):
    """A whisper the DM wrote before a restart is still listed after it."""
    dm = f"dm-{uuid4().hex[:6]}"
    camp_id, sess_id = await _setup_dm(dm)
    client = TestClient(process.app)
    created = client.post(
        "/api/v1/watcher/whispers",
        json={
            "session_id": sess_id,
            "campaign_id": camp_id,
            "whisper_type": "custom_note",
            "content": "The archer hides behind the pillar.",
        },
        headers=_headers(dm),
    )
    assert created.status_code == 200, created.text
    whisper_id = created.json()["whisper_id"]

    process.restart()
    listed = TestClient(process.app).get(
        f"/api/v1/watcher/whispers?session_id={sess_id}&campaign_id={camp_id}",
        headers=_headers(dm),
    )
    assert listed.status_code == 200, listed.text
    assert whisper_id in [w["whisper_id"] for w in listed.json()["whispers"]]
