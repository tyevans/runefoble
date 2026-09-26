"""Blackbox TDD test suite for Soundscape Tension & Tactical Foley (TASK-0095).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Tests dynamic encounter tension scoring, combat event reactivity,
tactical foley cue triggers, and SpiceDB Zanzibar authorization.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_events import (
    CombatEncounterStarted,
    CombatRoundAdvanced,
    CombatStarted,
    SoundscapeCueTriggered,
    SoundscapeTensionUpdated,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from soundscape.dependencies import (
    handle_incoming_domain_event,
    reset_dependencies,
    set_event_bus,
)
from soundscape.main import app
from soundscape.scoring import calculate_encounter_tension, derive_stem_profile


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean aggregate, mixer, and bus states before and after each test."""
    reset_dependencies()
    yield
    reset_dependencies()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_soundscape_combat_cloudevents_registration():
    """Verify soundscape cue and tension domain events register with CloudEvents."""
    cue_cls = get_event_class_or_none("runefoble.events.soundscape.cue_triggered")
    assert cue_cls is not None
    assert cue_cls is SoundscapeCueTriggered

    tension_cls = get_event_class_or_none("runefoble.events.soundscape.tension_updated")
    assert tension_cls is not None
    assert tension_cls is SoundscapeTensionUpdated

    assert CombatStarted is CombatEncounterStarted
    assert get_event_class_or_none("CombatRoundAdvanced") is CombatRoundAdvanced

    event = SoundscapeCueTriggered(
        session_id="session-tomb-14",
        cue_id="cue-fireball-1",
        cue_type="spell",
        sound_url="http://silo:9000/runefoble-assets/audio/foley/fireball.ogg",
        volume_gain=1.0,
        duck_music=True,
    )
    ce = event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.soundscape.cue_triggered"
    assert ce["data"]["session_id"] == "session-tomb-14"
    assert ce["data"]["cue_id"] == "cue-fireball-1"


def test_tension_scoring_exploration_and_combat():
    """Verify tension metric calculation across ambient and escalating combat states."""
    ambient_tension = calculate_encounter_tension(
        combat_active=False, combat_round=0, enemy_cr_balance=0.5
    )
    assert 0 <= ambient_tension <= 25
    assert derive_stem_profile(ambient_tension) == "exploration"

    early_combat = calculate_encounter_tension(
        combat_active=True,
        combat_round=1,
        enemy_cr_balance=1.0,
        lowest_party_health_ratio=1.0,
    )
    assert early_combat == 50
    assert derive_stem_profile(early_combat) == "tension"

    mid_combat = calculate_encounter_tension(
        combat_active=True,
        combat_round=3,
        enemy_cr_balance=3.0,
        lowest_party_health_ratio=0.5,
    )
    assert 60 <= mid_combat < 85
    assert derive_stem_profile(mid_combat) == "combat"

    critical_combat = calculate_encounter_tension(
        combat_active=True,
        combat_round=4,
        enemy_cr_balance=4.0,
        lowest_party_health_ratio=0.15,
    )
    assert critical_combat >= 85
    assert derive_stem_profile(critical_combat) == "boss"


def test_trigger_tactical_foley_cue_frontdoor(client: TestClient):
    """Verify POST /api/v1/soundscape/cue triggers sound FX and records event."""
    payload = {
        "session_id": "session-tomb-14",
        "cue_name": "fireball",
        "cue_type": "spell",
        "volume_gain": 1.0,
        "duck_music": True,
    }
    resp = client.post("/api/v1/soundscape/cue", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "triggered"
    assert data["cue_name"] == "fireball"
    assert "fireball.ogg" in data["sound_url"]
    assert data["duck_music"] is True


def test_tension_calculation_and_status_frontdoors(client: TestClient):
    """Verify GET /tension and POST /tension/calculate adaptively adjust stems."""
    calc_payload = {
        "session_id": "session-tomb-14",
        "combat_active": True,
        "combat_round": 2,
        "enemy_cr_balance": 2.5,
        "lowest_party_health_ratio": 0.4,
    }
    calc_resp = client.post("/api/v1/soundscape/tension/calculate", json=calc_payload)
    assert calc_resp.status_code == 200
    data = calc_resp.json()
    assert data["session_id"] == "session-tomb-14"
    assert data["tension_score"] >= 60
    assert data["stem_profile"] in ("combat", "boss")

    get_resp = client.get("/api/v1/soundscape/tension?session_id=session-tomb-14")
    assert get_resp.status_code == 200
    status_data = get_resp.json()
    assert status_data["session_id"] == "session-tomb-14"
    assert status_data["tension_score"] == data["tension_score"]
    assert status_data["stem_profile"] == data["stem_profile"]


@pytest.mark.asyncio
async def test_soundscape_combat_event_bus_reactivity():
    """Verify CombatEncounterStarted and CombatRoundAdvanced publication to Redis Stream."""
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)

    combat_start_event = CombatEncounterStarted(
        aggregate_id=uuid4(),
        session_id="session-tomb-14",
        round_number=1,
        combatants=[{"name": "Goblin", "cr": 2.0}],
    )
    await handle_incoming_domain_event(combat_start_event)

    stream_key = "runefoble.events.soundscape"
    assert stream_key in mock_redis.streams
    events_in_stream = mock_redis.streams[stream_key]
    assert len(events_in_stream) >= 1
    _, event_data = events_in_stream[-1]
    assert event_data["event_type"] == "runefoble.events.soundscape.track_changed"

    round_event = CombatRoundAdvanced(
        aggregate_id=uuid4(),
        session_id="session-tomb-14",
        round_number=3,
        active_combatant_id="comb-123",
    )
    await handle_incoming_domain_event(round_event)
    events_in_stream = mock_redis.streams[stream_key]
    assert len(events_in_stream) >= 2


@pytest.mark.asyncio
async def test_soundscape_zanzibar_authorization(client: TestClient):
    """Verify Zanzibar authorization enforces caller permissions for DM mood override."""
    from soundscape.dependencies import get_spicedb_client

    async def mock_deny(*args: Any, **kwargs: Any) -> bool:
        return False

    client.app.dependency_overrides[get_spicedb_client] = lambda: type(
        "MockSpiceDB", (), {"check_permission": mock_deny}
    )()

    resp = client.post(
        "/api/v1/soundscape/override",
        json={"session_id": "session-tomb-14", "mood": "boss"},
        headers={"x-user-id": "unauthorized-intruder"},
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]

    client.app.dependency_overrides.clear()
