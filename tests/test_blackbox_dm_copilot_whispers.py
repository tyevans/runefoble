"""Blackbox TDD test suite for DM Co-Pilot Whispers (TASK-0093).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Public HTTP REST API whisper endpoints in the_watcher.main
- Standard CloudEvent publication (DMNarrativeWhispered)
- Object-level Zanzibar authorization via SpiceDB schema (dungeon_master relation)
- Microfrontend manifest exposure
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient
from runefoble_events import DMNarrativeWhispered
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from the_watcher.dependencies import (
    get_copilot_engine,
    get_spicedb_client,
    set_event_bus,
    set_spicedb_client,
)
from the_watcher.main import app


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


def test_narrative_whispered_cloudevent_registration():
    """Verify DMNarrativeWhispered is registered in EventRegistry and conforms to CloudEvents."""
    cls = get_event_class_or_none("runefoble.events.watcher.narrative_whispered")
    assert cls is not None
    assert cls == DMNarrativeWhispered

    event = DMNarrativeWhispered(
        whisper_id="whisp-123",
        session_id="sess-456",
        campaign_id="camp-789",
        whisper_type="monster_tactics",
        content="Goblins plan a flank attack.",
        recipient_role="dungeon_master",
    )
    ce = event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.watcher.narrative_whispered"
    assert ce["data"]["whisper_id"] == "whisp-123"
    assert ce["data"]["recipient_role"] == "dungeon_master"


@pytest.mark.asyncio
async def test_zanzibar_whispers_dm_authorization_enforcement(client: TestClient):
    """Verify non-DM users cannot access whisper channels while authorized DMs succeed."""
    spicedb: SpiceDBClient = get_spicedb_client()
    campaign_id, session_id = str(uuid4()), str(uuid4())
    authorized_dm = f"dm-{uuid4().hex[:6]}"
    unauthorized_player = f"player-{uuid4().hex[:6]}"

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

    # Unauthorized player attempts to read whispers -> 403 Forbidden
    res_get_unauth = client.get(
        f"/api/v1/watcher/whispers?session_id={session_id}&campaign_id={campaign_id}",
        headers={"X-User-Id": unauthorized_player},
    )
    assert res_get_unauth.status_code == 403
    assert "Forbidden" in res_get_unauth.json()["detail"]

    # Unauthorized player attempts to create a whisper -> 403 Forbidden
    res_post_unauth = client.post(
        "/api/v1/watcher/whispers",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "whisper_type": "monster_tactics",
            "content": "Secret player plan",
        },
        headers={"X-User-Id": unauthorized_player},
    )
    assert res_post_unauth.status_code == 403

    # Authorized DM reads whispers -> 200 OK
    res_get_auth = client.get(
        f"/api/v1/watcher/whispers?session_id={session_id}&campaign_id={campaign_id}",
        headers={"X-User-Id": authorized_dm},
    )
    assert res_get_auth.status_code == 200
    assert "whispers" in res_get_auth.json()


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

    types = ["atmospheric_hint", "monster_tactics", "passive_perception"]
    for i, w_type in enumerate(types):
        res = client.post(
            "/api/v1/watcher/whispers",
            json={
                "session_id": session_id,
                "campaign_id": campaign_id,
                "whisper_type": w_type,
                "content": f"Custom whisper content {i} for {w_type}",
            },
            headers={"X-User-Id": dm_user},
        )
        assert res.status_code == 200

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

    res_filter = client.get(
        f"/api/v1/watcher/whispers?session_id={session_id}&campaign_id={campaign_id}&whisper_type=monster_tactics",
        headers={"X-User-Id": dm_user},
    )
    assert res_filter.status_code == 200
    assert res_filter.json()["whispers"][0]["whisper_type"] == "monster_tactics"


@pytest.mark.asyncio
async def test_dm_whispers_generation(client: TestClient):
    """Verify automated whisper generation for scenes, tactics, and perception cues."""
    spicedb: SpiceDBClient = get_spicedb_client()
    campaign_id, session_id, dm_user = str(uuid4()), str(uuid4()), "dm_evelyn"
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )

    res_gen = client.post(
        "/api/v1/watcher/whispers/generate",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "scene_context": "Deep subterranean cave",
            "threat_level": "hard",
        },
        headers={"X-User-Id": dm_user},
    )
    assert res_gen.status_code == 200
    whispers = res_gen.json()
    assert len(whispers) >= 3
    assert any(w["whisper_type"] == "monster_tactics" for w in whispers)


def test_watcher_ui_manifest_includes_whisper_bar(client: TestClient):
    """Verify that runefoble-dm-whisper-bar is advertised in The Watcher's UI manifest."""
    res = client.get("/ui/manifest")
    assert res.status_code == 200
    manifest = res.json()
    assert manifest["service"] == "the_watcher"
    assert "runefoble-dm-whisper-bar" in manifest["components"]
