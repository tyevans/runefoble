"""Blackbox TDD test suite for DM Co-Pilot Action Interceptor and Veto Engine (TASK-0093).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Operates strictly through public frontdoors: HTTP REST endpoints, CloudEvents, and Zanzibar auth.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_events import (
    WatcherActionApproved,
    WatcherActionModified,
    WatcherActionProposed,
    WatcherActionVetoed,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from the_watcher.dependencies import (
    get_copilot_engine,
    get_spicedb_client,
    set_event_bus,
    set_spicedb_client,
)
from the_watcher.main import app
from the_watcher.models import ProposeActionRequest


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean SpiceDB, CopilotEngine, and event bus state before and after each test."""
    set_spicedb_client(MockSpiceDBClient())
    set_event_bus(RedisStreamsEventBus(client=MockAsyncRedis()))
    engine = get_copilot_engine()
    engine.clear()
    yield
    engine.clear()
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


def _propose(client: TestClient, sess_id: str, camp_id: str, **kwargs) -> str:
    body = {
        "session_id": sess_id,
        "campaign_id": camp_id,
        "actor_name": "Goblin",
        "action_type": "attack",
        "description": "Attacks target",
        "pause_window_ms": 3000,
        **kwargs,
    }
    res = client.post("/api/v1/watcher/actions/propose", json=body)
    assert res.status_code == 200
    return res.json()["action_id"]


def test_copilot_action_cloudevents_registration():
    """Verify action domain events are registered in EventRegistry and conform to CloudEvents."""
    events = [
        ("runefoble.events.watcher.action_proposed", WatcherActionProposed),
        ("runefoble.events.watcher.action_vetoed", WatcherActionVetoed),
        ("runefoble.events.watcher.action_approved", WatcherActionApproved),
        ("runefoble.events.watcher.action_modified", WatcherActionModified),
    ]
    for type_name, expected_cls in events:
        assert get_event_class_or_none(type_name) == expected_cls

    veto = WatcherActionVetoed(
        action_id="act-1",
        session_id="sess-1",
        campaign_id="camp-1",
        vetoed_by="dm_evelyn",
        reason="Pacing",
        original_action={"action_type": "attack", "target": "Valeros"},
    )
    ce = veto.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.watcher.action_vetoed"
    assert ce["data"]["action_id"] == "act-1"


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
    action_id = _propose(client, sess_id, camp_id)

    # Unauthorized attempts -> 403
    base = {"action_id": action_id, "session_id": sess_id, "campaign_id": camp_id}
    for ep, payload in [
        ("/api/v1/watcher/veto", {**base, "reason": "No"}),
        ("/api/v1/watcher/approve", base),
        ("/api/v1/watcher/modify", {**base, "description": "Mod"}),
    ]:
        res = client.post(ep, json=payload, headers={"X-User-Id": player})
        assert res.status_code == 403
        assert "Forbidden" in res.json()["detail"]

    res_list = client.get(
        f"/api/v1/watcher/actions/pending?session_id={sess_id}&campaign_id={camp_id}",
        headers={"X-User-Id": player},
    )
    assert res_list.status_code == 403

    # Authorized DM veto succeeds
    res_veto = client.post(
        "/api/v1/watcher/veto",
        json={**base, "reason": "DM override"},
        headers={"X-User-Id": dm_user},
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
        headers={"X-User-Id": "dm_evelyn"},
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
        headers={"X-User-Id": "dm_evelyn"},
    )
    assert res_veto.status_code == 200
    assert res_veto.json()["status"] == "vetoed"

    pending = get_copilot_engine().get_pending_action(action_id)
    assert pending is not None and pending.status == "vetoed" and pending.vetoed_by == "dm_evelyn"


@pytest.mark.asyncio
async def test_dm_immediate_approve_frontdoor(client: TestClient):
    """Verify DM can approve an intercepted action immediately."""
    camp_id, sess_id = await _setup_dm("dm_evelyn")
    action_id = _propose(client, sess_id, camp_id)

    res_appr = client.post(
        "/api/v1/watcher/approve",
        json={"action_id": action_id, "session_id": sess_id, "campaign_id": camp_id},
        headers={"X-User-Id": "dm_evelyn"},
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "approved"
    assert get_copilot_engine().get_pending_action(action_id).status == "approved"


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
        headers={"X-User-Id": "dm_evelyn"},
    )
    assert res_mod.status_code == 200
    assert res_mod.json()["status"] == "approved"
    assert res_mod.json()["target"] == "Paladin Shield"
    assert res_mod.json()["parameters"]["darts"] == 1


@pytest.mark.asyncio
async def test_pause_window_timeout_auto_executes():
    """Verify that if no veto occurs, the action automatically commits upon pause window expiry."""
    engine, executed = get_copilot_engine(), False

    async def on_execute():
        nonlocal executed
        executed = True

    action = engine.propose_action(
        req=ProposeActionRequest(
            session_id="sess-auto",
            actor_name="Goblin Scout",
            action_type="scout_move",
            description="Moves 2 squares east",
            pause_window_ms=50,
        ),
        on_execute=on_execute,
    )
    assert action.status == "pending" and not executed
    await asyncio.sleep(0.1)
    assert action.status == "executed" and executed
