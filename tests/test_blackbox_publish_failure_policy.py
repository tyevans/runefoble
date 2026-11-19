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
from runefoble_auth.factory import get_spicedb_client
from the_watcher.main import app

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.spicedb_factory import bind_session_to_campaign
from tests.helpers.watcher_copilot_stores import install_fresh_copilot_stores
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


class FailingRedis(MockAsyncRedis):
    """Redis double whose stream writes always fail, as when the broker is unreachable."""

    async def xadd(self, *args, **kwargs):
        raise ConnectionError("redis unavailable (test double)")


@pytest.fixture(autouse=True)
def clean_environment(seam_restorer: SeamRestorer):
    install_fresh_copilot_stores(seam_restorer)
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})


async def _setup_dm(dm_user: str = "dm_evelyn") -> tuple[str, str]:
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


def _publish_failures(client: TestClient) -> int:
    return client.get("/healthz").json()["event_publish_failures"]


@pytest.mark.asyncio
async def test_propose_returns_200_when_redis_is_down(client: TestClient, use_redis_client):
    """A proposal is stored in the pending-action aggregate. Redis being down does not fail it."""
    camp_id, sess_id = await _setup_dm("dm_evelyn")
    before = _publish_failures(client)

    use_redis_client(FailingRedis())
    res = client.post(
        "/api/v1/watcher/actions/propose",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm_evelyn')}"},
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
    assert _publish_failures(client) == before
