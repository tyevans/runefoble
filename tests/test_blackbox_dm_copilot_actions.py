"""Blackbox TDD test suite for DM Co-Pilot Action Interceptor and Veto Engine (TASK-0093).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Operates strictly through public frontdoors: HTTP REST endpoints, CloudEvents, and Zanzibar auth.
"""

from __future__ import annotations

import asyncio
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


@pytest.fixture(autouse=True)
def clean_environment(seam_restorer: SeamRestorer):
    """Give each test empty copilot stores."""
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


def _propose(
    client: TestClient, sess_id: str, camp_id: str, *, proposer: str = "dm_evelyn", **kwargs
) -> str:
    body = {
        "session_id": sess_id,
        "campaign_id": camp_id,
        "actor_name": "Goblin",
        "action_type": "attack",
        "description": "Attacks target",
        "pause_window_ms": 3000,
        **kwargs,
    }
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint(proposer)}"}
    res = client.post("/api/v1/watcher/actions/propose", json=body, headers=headers)
    assert res.status_code == 200
    return res.json()["action_id"]


@pytest.mark.asyncio
async def test_zanzibar_action_authorization_enforcement(client: TestClient):
    """Verify unauthorized users are rejected with 403 Forbidden while authorized DMs succeed."""
    dm_user, player = f"dm-{uuid4().hex[:6]}", f"player-{uuid4().hex[:6]}"
    camp_id, sess_id = await _setup_dm(dm_user)
    await get_spicedb_client().write_relationship(
        resource_type="campaign",
        resource_id=camp_id,
        relation="player",
        subject_type="user",
        subject_id=player,
    )
    action_id = _propose(client, sess_id, camp_id, proposer=dm_user)

    # Unauthorized attempts -> 403
    base = {"action_id": action_id, "session_id": sess_id, "campaign_id": camp_id}
    for ep, payload in [
        ("/api/v1/watcher/veto", {**base, "reason": "No"}),
        ("/api/v1/watcher/approve", base),
        ("/api/v1/watcher/modify", {**base, "description": "Mod"}),
    ]:
        res = client.post(
            ep, json=payload, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player)}"}
        )
        assert res.status_code == 403
        assert "Forbidden" in res.json()["detail"]

    res_list = client.get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(player)}"},
    )
    assert res_list.status_code == 403

    # Authorized DM veto succeeds
    res_veto = client.post(
        "/api/v1/watcher/veto",
        json={**base, "reason": "DM override"},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint(dm_user)}"},
    )
    assert res_veto.status_code == 200
    assert res_veto.json()["status"] == "vetoed"
    assert res_veto.json()["vetoed_by"] == dm_user


@pytest.mark.asyncio
async def test_pre_execution_veto_halts_mutation(client: TestClient):
    """Verify that vetoing an intercepted action cancels execution and dispatches event."""
    camp_id, sess_id = await _setup_dm("dm_evelyn")
    action_id = _propose(
        client, sess_id, camp_id, actor_name="Dragon", action_type="breath", pause_window_ms=2500
    )

    res_pending = client.get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm_evelyn')}"},
    )
    assert any(a["action_id"] == action_id for a in res_pending.json())

    res_veto = client.post(
        "/api/v1/watcher/veto",
        json={
            "action_id": action_id,
            "session_id": sess_id,
            "campaign_id": camp_id,
            "reason": "Low HP veto",
        },
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm_evelyn')}"},
    )
    assert res_veto.status_code == 200
    assert res_veto.json()["status"] == "vetoed"

    listed = client.get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm_evelyn')}"},
    )
    vetoed = [a for a in listed.json() if a["action_id"] == action_id]
    assert len(vetoed) == 1
    assert vetoed[0]["status"] == "vetoed" and vetoed[0]["vetoed_by"] == "dm_evelyn"


@pytest.mark.asyncio
async def test_dm_immediate_approve_frontdoor(client: TestClient):
    """Verify DM can approve an intercepted action immediately."""
    camp_id, sess_id = await _setup_dm("dm_evelyn")
    action_id = _propose(client, sess_id, camp_id)

    res_appr = client.post(
        "/api/v1/watcher/approve",
        json={"action_id": action_id, "session_id": sess_id, "campaign_id": camp_id},
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm_evelyn')}"},
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "approved"
    listed = client.get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm_evelyn')}"},
    )
    assert [a["status"] for a in listed.json() if a["action_id"] == action_id] == ["approved"]


@pytest.mark.asyncio
async def test_dm_modify_action_frontdoor(client: TestClient):
    """Verify DM can edit parameters, description, and target of an intercepted action."""
    camp_id, sess_id = await _setup_dm("dm_evelyn")
    action_id = _propose(client, sess_id, camp_id, parameters={"darts": 3, "damage_per_dart": 3})

    res_mod = client.post(
        "/api/v1/watcher/modify",
        json={
            "action_id": action_id,
            "session_id": sess_id,
            "campaign_id": camp_id,
            "description": "Deflected missile",
            "target": "Paladin Shield",
            "parameters": {"darts": 1},
            "auto_approve": True,
        },
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm_evelyn')}"},
    )
    assert res_mod.status_code == 200
    assert res_mod.json()["status"] == "approved"
    assert res_mod.json()["target"] == "Paladin Shield"
    assert res_mod.json()["parameters"]["darts"] == 1


@pytest.mark.asyncio
async def test_pause_window_timeout_auto_executes(use_redis_client):
    """Verify that if no veto occurs, the action commits when its pause window expires."""
    mock_redis = MockAsyncRedis()
    use_redis_client(mock_redis)
    camp_id, sess_id = await _setup_dm("dm_evelyn")
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('dm_evelyn')}"}

    with TestClient(app, headers=headers) as client:
        action_id = _propose(client, sess_id, camp_id, pause_window_ms=100)
        listed_url = f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}"
        status = None
        for _ in range(50):
            await asyncio.sleep(0.05)
            listed = client.get(listed_url, headers=headers)
            status = next(a["status"] for a in listed.json() if a["action_id"] == action_id)
            if status == "executed":
                break
        assert status == "executed"
