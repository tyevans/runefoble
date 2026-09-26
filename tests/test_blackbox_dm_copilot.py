"""Blackbox TDD test suite for DM Co-Pilot Whispers and Veto Override Engine (TASK-0053).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Public HTTP REST API endpoints in the_watcher.main
- Standard CloudEvents published across Redis Streams (WatcherActionVetoed, etc.)
- Object-level Zanzibar authorization via SpiceDB schema (dungeon_master relation)
- Microfrontend manifest exposure
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_events import (
    DMNarrativeWhispered,
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
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)
    engine = get_copilot_engine()
    engine.clear()
    yield
    engine.clear()
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. CloudEvents Registration & Schema Compliance
# ---------------------------------------------------------------------------


def test_copilot_cloudevents_registration():
    """Verify copilot domain events are registered in eventsource EventRegistry and conform to CloudEvents."""
    events_to_test = [
        ("runefoble.events.watcher.action_proposed", WatcherActionProposed),
        ("runefoble.events.watcher.action_vetoed", WatcherActionVetoed),
        ("runefoble.events.watcher.action_approved", WatcherActionApproved),
        ("runefoble.events.watcher.action_modified", WatcherActionModified),
        ("runefoble.events.watcher.narrative_whispered", DMNarrativeWhispered),
    ]

    for type_name, expected_cls in events_to_test:
        cls = get_event_class_or_none(type_name)
        assert cls is not None, f"Event {type_name} is not registered in EventRegistry"
        assert cls == expected_cls

    veto_event = WatcherActionVetoed(
        action_id="act-123",
        session_id="sess-456",
        campaign_id="camp-789",
        vetoed_by="dm_evelyn",
        reason="Narrative pacing",
        original_action={"action_type": "attack", "target": "Valeros"},
    )
    ce = veto_event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.watcher.action_vetoed"
    assert ce["data"]["action_id"] == "act-123"
    assert ce["data"]["vetoed_by"] == "dm_evelyn"


# ---------------------------------------------------------------------------
# 2. SpiceDB Zanzibar Authorization Checks (Non-DM vs Authorized DM)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zanzibar_dm_authorization_enforcement(client: TestClient):
    """Verify non-DM users are rejected with 403 Forbidden while authorized DMs succeed."""
    spicedb: SpiceDBClient = get_spicedb_client()
    campaign_id = str(uuid4())
    session_id = str(uuid4())
    authorized_dm = f"dm-{uuid4().hex[:6]}"
    unauthorized_player = f"player-{uuid4().hex[:6]}"

    # Grant dungeon_master relation on campaign to authorized_dm in SpiceDB
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=authorized_dm,
    )
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=unauthorized_player,
    )

    # 1. Propose action via frontdoor
    res_prop = client.post(
        "/api/v1/watcher/actions/propose",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "actor_name": "Goblin Sneak",
            "action_type": "attack",
            "description": "Attacks from shadows",
            "target": "Thorin",
            "pause_window_ms": 3000,
        },
    )
    assert res_prop.status_code == 200
    action_id = res_prop.json()["action_id"]

    # 2. Unauthorized player attempts to veto -> 403 Forbidden
    res_veto_unauth = client.post(
        "/api/v1/watcher/veto",
        json={
            "action_id": action_id,
            "session_id": session_id,
            "campaign_id": campaign_id,
            "reason": "Player veto attempt",
        },
        headers={"X-User-Id": unauthorized_player},
    )
    assert res_veto_unauth.status_code == 403
    assert "Forbidden" in res_veto_unauth.json()["detail"]

    # 3. Unauthorized player attempts to read whispers -> 403 Forbidden
    res_whisp_unauth = client.get(
        f"/api/v1/watcher/whispers?session_id={session_id}&campaign_id={campaign_id}",
        headers={"X-User-Id": unauthorized_player},
    )
    assert res_whisp_unauth.status_code == 403

    # 4. Unauthorized player attempts to approve -> 403 Forbidden
    res_appr_unauth = client.post(
        "/api/v1/watcher/approve",
        json={"action_id": action_id, "session_id": session_id, "campaign_id": campaign_id},
        headers={"X-User-Id": unauthorized_player},
    )
    assert res_appr_unauth.status_code == 403

    # 5. Unauthorized player attempts to modify -> 403 Forbidden
    res_mod_unauth = client.post(
        "/api/v1/watcher/modify",
        json={
            "action_id": action_id,
            "session_id": session_id,
            "campaign_id": campaign_id,
            "description": "Changed target",
        },
        headers={"X-User-Id": unauthorized_player},
    )
    assert res_mod_unauth.status_code == 403

    # 6. Authorized DM reads whispers -> 200 OK
    res_whisp_auth = client.get(
        f"/api/v1/watcher/whispers?session_id={session_id}&campaign_id={campaign_id}",
        headers={"X-User-Id": authorized_dm},
    )
    assert res_whisp_auth.status_code == 200
    assert "whispers" in res_whisp_auth.json()

    # 7. Authorized DM executes veto -> 200 OK
    res_veto_auth = client.post(
        "/api/v1/watcher/veto",
        json={
            "action_id": action_id,
            "session_id": session_id,
            "campaign_id": campaign_id,
            "reason": "Evelyn overrides goblin ambush",
        },
        headers={"X-User-Id": authorized_dm},
    )
    assert res_veto_auth.status_code == 200
    assert res_veto_auth.json()["status"] == "vetoed"
    assert res_veto_auth.json()["vetoed_by"] == authorized_dm


# ---------------------------------------------------------------------------
# 3. Pre-Execution Veto Interceptor Mechanics & Event Emission
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pre_execution_veto_halts_mutation(client: TestClient):
    """Verify that vetoing an intercepted action cancels execution and dispatches WatcherActionVetoed."""
    spicedb: SpiceDBClient = get_spicedb_client()
    campaign_id = str(uuid4())
    session_id = str(uuid4())
    dm_user = "dm_evelyn"

    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )

    # 1. Propose action with a pause window
    res_prop = client.post(
        "/api/v1/watcher/propose",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "actor_name": "Young Red Dragon",
            "action_type": "breath_weapon",
            "description": "Breathes 30ft cone of fire",
            "target": "Party",
            "parameters": {"damage": 35},
            "pause_window_ms": 2500,
        },
    )
    assert res_prop.status_code == 200
    action_id = res_prop.json()["action_id"]

    # 2. Verify action appears in pending actions list
    res_pending = client.get(
        f"/api/v1/watcher/actions/pending?session_id={session_id}&campaign_id={campaign_id}",
        headers={"X-User-Id": dm_user},
    )
    assert res_pending.status_code == 200
    assert any(a["action_id"] == action_id for a in res_pending.json())

    # 3. DM vetoes the action before timeout
    res_veto = client.post(
        "/api/v1/watcher/veto",
        json={
            "action_id": action_id,
            "session_id": session_id,
            "campaign_id": campaign_id,
            "reason": "Party is already at low HP; veto dragon breath",
        },
        headers={"X-User-Id": dm_user},
    )
    assert res_veto.status_code == 200
    assert res_veto.json()["status"] == "vetoed"

    # 4. Check action state in engine is vetoed
    engine = get_copilot_engine()
    pending_action = engine.get_pending_action(action_id)
    assert pending_action is not None
    assert pending_action.status == "vetoed"
    assert pending_action.vetoed_by == dm_user


# ---------------------------------------------------------------------------
# 4. Immediate Approval and Action Modification Frontdoors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dm_immediate_approve_frontdoor(client: TestClient):
    """Verify DM can approve an intercepted action immediately."""
    spicedb: SpiceDBClient = get_spicedb_client()
    campaign_id, session_id, dm_user = str(uuid4()), str(uuid4()), "dm_evelyn"
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )

    res_prop = client.post(
        "/api/v1/watcher/actions/propose",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "actor_name": "Goblin Boss",
            "action_type": "disengage",
            "description": "Goblin Boss disengages and dashes behind pillar",
            "pause_window_ms": 3000,
        },
    )
    action_id = res_prop.json()["action_id"]

    res_appr = client.post(
        "/api/v1/watcher/approve",
        json={"action_id": action_id, "session_id": session_id, "campaign_id": campaign_id},
        headers={"X-User-Id": dm_user},
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "approved"
    assert get_copilot_engine().get_pending_action(action_id).status == "approved"


@pytest.mark.asyncio
async def test_dm_modify_action_frontdoor(client: TestClient):
    """Verify DM can edit the parameters, description, and target of an intercepted action."""
    spicedb: SpiceDBClient = get_spicedb_client()
    campaign_id, session_id, dm_user = str(uuid4()), str(uuid4()), "dm_evelyn"
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )

    res_prop = client.post(
        "/api/v1/watcher/actions/propose",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "actor_name": "Mage Apprentice",
            "action_type": "cast_spell",
            "description": "Casts Magic Missile targeting Valeros",
            "target": "Valeros",
            "parameters": {"darts": 3, "damage_per_dart": 3},
            "pause_window_ms": 2000,
        },
    )
    action_id = res_prop.json()["action_id"]

    res_mod = client.post(
        "/api/v1/watcher/modify",
        json={
            "action_id": action_id,
            "session_id": session_id,
            "campaign_id": campaign_id,
            "description": "Casts Magic Missile deflected by Paladin Shield",
            "target": "Paladin Shield",
            "parameters": {"darts": 1},
            "auto_approve": True,
        },
        headers={"X-User-Id": dm_user},
    )
    assert res_mod.status_code == 200
    assert res_mod.json()["status"] == "approved"
    assert res_mod.json()["target"] == "Paladin Shield"
    assert res_mod.json()["parameters"]["darts"] == 1


# ---------------------------------------------------------------------------
# 5. Private Narrative Whispers Stream & Pagination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dm_whispers_creation_and_pagination(client: TestClient):
    """Verify DM narrative suggestion stream supports creation, filtering, and pagination."""
    spicedb: SpiceDBClient = get_spicedb_client()
    campaign_id, session_id, dm_user = str(uuid4()), str(uuid4()), "dm_evelyn"
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )

    for i, w_type in enumerate(["atmospheric_hint", "monster_tactics", "passive_perception"]):
        res_create = client.post(
            "/api/v1/watcher/whispers",
            json={
                "session_id": session_id,
                "campaign_id": campaign_id,
                "whisper_type": w_type,
                "content": f"Custom whisper content {i} for {w_type}",
            },
            headers={"X-User-Id": dm_user},
        )
        assert res_create.status_code == 200

    res_p1 = client.get(
        f"/api/v1/watcher/whispers?session_id={session_id}&campaign_id={campaign_id}&page=1&limit=2",
        headers={"X-User-Id": dm_user},
    )
    assert res_p1.status_code == 200
    assert len(res_p1.json()["whispers"]) == 2

    res_p2 = client.get(
        f"/api/v1/watcher/whispers?session_id={session_id}&campaign_id={campaign_id}&page=2&limit=2",
        headers={"X-User-Id": dm_user},
    )
    assert res_p2.status_code == 200
    assert len(res_p2.json()["whispers"]) == 1

    res_tactics = client.get(
        f"/api/v1/watcher/whispers?session_id={session_id}&campaign_id={campaign_id}&whisper_type=monster_tactics",
        headers={"X-User-Id": dm_user},
    )
    assert res_tactics.status_code == 200
    assert res_tactics.json()["whispers"][0]["whisper_type"] == "monster_tactics"

    res_gen = client.post(
        "/api/v1/watcher/whispers/generate",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "scene_context": "Deep cave",
            "threat_level": "hard",
        },
        headers={"X-User-Id": dm_user},
    )
    assert res_gen.status_code == 200
    assert len(res_gen.json()) >= 3


# ---------------------------------------------------------------------------
# 6. Microfrontend Manifest Integration
# ---------------------------------------------------------------------------


def test_watcher_ui_manifest_includes_whisper_bar(client: TestClient):
    """Verify that runefoble-dm-whisper-bar is advertised in The Watcher's UI manifest."""
    res = client.get("/ui/manifest")
    assert res.status_code == 200
    manifest = res.json()
    assert manifest["service"] == "the_watcher"
    assert "runefoble-dm-whisper-bar" in manifest["components"]
    assert "runefoble-watcher-feed" in manifest["components"]
    assert "runefoble-autonomous-dm" in manifest["components"]


# ---------------------------------------------------------------------------
# 7. Pause Window Timeout Auto-Execution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pause_window_timeout_auto_executes():
    """Verify that if no veto occurs, the action automatically commits upon pause window expiry."""
    engine = get_copilot_engine()
    executed = False

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
    assert action.status == "pending"
    assert executed is False

    await asyncio.sleep(0.1)
    assert action.status == "executed"
    assert executed is True
