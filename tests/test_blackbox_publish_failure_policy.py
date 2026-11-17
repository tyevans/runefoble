"""Blackbox tests for the domain event publish failure policy (TASK-0564).

Decision routes return 503 when the audit event cannot be published, and the pending
action is left unchanged. Side-effect routes return 200 and increment the
``event_publish_failures`` counter on ``/healthz``.

The failing Redis client is a process-boundary double. Every other path uses the public
HTTP frontdoors.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_platform.redis_bus import RedisStreamsEventBus
from the_watcher.dependencies import (
    get_copilot_engine,
    get_spicedb_client,
    set_event_bus,
    set_spicedb_client,
)
from the_watcher.main import app

from tests.helpers.mock_redis import MockAsyncRedis


class FailingRedis(MockAsyncRedis):
    """Redis double whose stream writes always fail, as when the broker is unreachable."""

    async def xadd(self, *args, **kwargs):
        raise ConnectionError("redis unavailable (test double)")


@pytest.fixture(autouse=True)
def clean_environment():
    set_spicedb_client(MockSpiceDBClient())
    set_event_bus(RedisStreamsEventBus(client=MockAsyncRedis()))
    get_copilot_engine().clear()
    yield
    get_copilot_engine().clear()
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


async def _setup_dm(dm_user: str = "dm_evelyn") -> tuple[str, str]:
    camp_id, sess_id = str(uuid4()), str(uuid4())
    await get_spicedb_client().write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )
    return camp_id, sess_id


def _propose(client: TestClient, sess_id: str, camp_id: str) -> str:
    res = client.post(
        "/api/v1/watcher/actions/propose",
        json={
            "session_id": sess_id,
            "campaign_id": camp_id,
            "actor_name": "Dragon",
            "action_type": "breath",
            "description": "Breathes fire",
            "pause_window_ms": 60000,
        },
    )
    assert res.status_code == 200
    return res.json()["action_id"]


def _pending_status(client: TestClient, sess_id: str, camp_id: str, action_id: str) -> str:
    res = client.get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers={"X-User-Id": "dm_evelyn"},
    )
    assert res.status_code == 200
    return next(a["status"] for a in res.json() if a["action_id"] == action_id)


def _publish_failures(client: TestClient) -> int:
    return client.get("/healthz").json()["event_publish_failures"]


@pytest.mark.asyncio
async def test_veto_returns_503_and_action_stays_pending_when_event_unpublished(
    client: TestClient,
):
    """Fail before, pass after: a veto whose audit event cannot be written must not apply."""
    camp_id, sess_id = await _setup_dm("dm_evelyn")
    action_id = _propose(client, sess_id, camp_id)

    set_event_bus(RedisStreamsEventBus(client=FailingRedis()))
    res = client.post(
        "/api/v1/watcher/veto",
        json={"action_id": action_id, "session_id": sess_id, "campaign_id": camp_id},
        headers={"X-User-Id": "dm_evelyn"},
    )

    assert res.status_code == 503
    assert _pending_status(client, sess_id, camp_id, action_id) == "pending"


@pytest.mark.asyncio
async def test_approve_returns_503_and_action_stays_pending_when_event_unpublished(
    client: TestClient,
):
    """A failed approval must not commit the action or skip its audit event."""
    camp_id, sess_id = await _setup_dm("dm_evelyn")
    action_id = _propose(client, sess_id, camp_id)

    set_event_bus(RedisStreamsEventBus(client=FailingRedis()))
    res = client.post(
        "/api/v1/watcher/approve",
        json={"action_id": action_id, "session_id": sess_id, "campaign_id": camp_id},
        headers={"X-User-Id": "dm_evelyn"},
    )

    assert res.status_code == 503
    assert _pending_status(client, sess_id, camp_id, action_id) == "pending"


@pytest.mark.asyncio
async def test_side_effect_route_returns_200_and_counts_publish_failure(client: TestClient):
    """Fail before, pass after: a read-model side effect logs and counts, and does not fail."""
    camp_id, sess_id = await _setup_dm("dm_evelyn")
    before = _publish_failures(client)

    set_event_bus(RedisStreamsEventBus(client=FailingRedis()))
    res = client.post(
        "/api/v1/watcher/actions/propose",
        json={
            "session_id": sess_id,
            "campaign_id": camp_id,
            "actor_name": "Goblin",
            "action_type": "attack",
            "description": "Attacks target",
            "pause_window_ms": 60000,
        },
    )

    assert res.status_code == 200
    assert _publish_failures(client) == before + 1
