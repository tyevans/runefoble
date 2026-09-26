"""Blackbox TDD test suite for Dynamic Soundscape & Adaptive Audio Microservice (TASK-0050).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public frontdoors:
- Public HTTP REST API endpoints in soundscape.main
- Published standard CloudEvents over Redis Streams (SoundscapeTrackChanged, etc.)
- Autonomous reactivity to CombatStarted, CombatRoundAdvanced, and PlayerSpokeEvent
- WebAudio -12dB ducking coordinator and encounter tension scoring
- Object-level Zanzibar authorization via SpiceDB schema
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_events import (
    CombatEncounterStarted,
    CombatRoundAdvanced,
    CombatStarted,
    PlayerSpokeEvent,
    SoundscapeCueTriggered,
    SoundscapeDuckingToggled,
    SoundscapeTensionUpdated,
    SoundscapeTrackChanged,
)
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from soundscape.dependencies import (
    get_or_create_mixer,
    handle_incoming_domain_event,
    reset_dependencies,
    set_event_bus,
)
from soundscape.main import app
from soundscape.mixer import DUCKING_ATTENUATION_DB, DUCKING_LINEAR_MULTIPLIER, AudioStemMixer
from soundscape.scoring import calculate_encounter_tension, derive_stem_profile

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean aggregate, mixer, and bus states before and after each test."""
    reset_dependencies()
    yield
    reset_dependencies()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Event Registration & CloudEvents Compliance Tests
# ---------------------------------------------------------------------------


def test_soundscape_cloudevents_registration():
    """Verify soundscape domain events are registered in eventsource EventRegistry."""
    track_cls = get_event_class_or_none("runefoble.events.soundscape.track_changed")
    assert track_cls is not None
    assert track_cls is SoundscapeTrackChanged

    cue_cls = get_event_class_or_none("runefoble.events.soundscape.cue_triggered")
    assert cue_cls is not None
    assert cue_cls is SoundscapeCueTriggered

    tension_cls = get_event_class_or_none("runefoble.events.soundscape.tension_updated")
    assert tension_cls is not None
    assert tension_cls is SoundscapeTensionUpdated

    duck_cls = get_event_class_or_none("runefoble.events.soundscape.ducking_toggled")
    assert duck_cls is not None
    assert duck_cls is SoundscapeDuckingToggled

    # Check Combat aliases
    assert CombatStarted is CombatEncounterStarted
    assert get_event_class_or_none("CombatRoundAdvanced") is CombatRoundAdvanced

    # Verify CloudEvents serialization
    event = SoundscapeTrackChanged(
        session_id="session-tomb-14",
        track_id="track-combat-01",
        stem_profile="combat",
        tension_score=75,
        crossfade_duration_ms=1500,
        active_stems=["combat", "tension"],
    )
    ce = event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.soundscape.track_changed"
    assert ce["data"]["session_id"] == "session-tomb-14"
    assert ce["data"]["stem_profile"] == "combat"
    assert ce["data"]["tension_score"] == 75


# ---------------------------------------------------------------------------
# 2. Encounter Tension Scoring Engine Tests
# ---------------------------------------------------------------------------


def test_tension_scoring_exploration_and_combat():
    """Verify tension metric calculation across ambient and escalating combat states."""
    # 1. Ambient exploration: combat not active, low tension
    ambient_tension = calculate_encounter_tension(
        combat_active=False, combat_round=0, enemy_cr_balance=0.5
    )
    assert 0 <= ambient_tension <= 25
    assert derive_stem_profile(ambient_tension) == "exploration"

    # 2. Early combat encounter: base 40 + round 1 + CR 1.0 + healthy party
    early_combat = calculate_encounter_tension(
        combat_active=True,
        combat_round=1,
        enemy_cr_balance=1.0,
        lowest_party_health_ratio=1.0,
    )
    assert early_combat == 50  # 40 base + 5 round + 5 CR + 0 hp penalty
    assert derive_stem_profile(early_combat) == "tension"

    # 3. High intensity combat: round 3, CR 3.0, party hurt (50% HP)
    mid_combat = calculate_encounter_tension(
        combat_active=True,
        combat_round=3,
        enemy_cr_balance=3.0,
        lowest_party_health_ratio=0.5,
    )
    # 40 base + 15 round + 15 CR + 12 hp penalty = 82
    assert 60 <= mid_combat < 85
    assert derive_stem_profile(mid_combat) == "combat"

    # 4. Boss / Near-Death Climax: round 4, deadly CR 4.0, critical health < 25% (+15 bonus)
    critical_combat = calculate_encounter_tension(
        combat_active=True,
        combat_round=4,
        enemy_cr_balance=4.0,
        lowest_party_health_ratio=0.15,
    )
    assert critical_combat >= 85
    assert derive_stem_profile(critical_combat) == "boss"


# ---------------------------------------------------------------------------
# 3. Audio Stem Mixer & WebAudio -12dB Ducking Tests
# ---------------------------------------------------------------------------


def test_stem_mixer_attenuation_and_ducking():
    """Verify stem weights and -12dB ducking calculation (PRD-0010, US-0039)."""
    mixer = AudioStemMixer(stem_profile="combat", master_volume=1.0)
    gains = mixer.calculate_active_stem_gains()
    assert gains["combat"] == 1.0
    assert gains["boss"] == 0.2

    # Ducking attenuation: -12 dB = 10^(-12/20) ~ 0.2512
    assert DUCKING_ATTENUATION_DB == -12.0
    assert math.isclose(DUCKING_LINEAR_MULTIPLIER, 0.251188, rel_tol=1e-3)

    # Enable voice ducking
    mixer.set_ducking(True, reason="speech")
    assert mixer.is_ducked is True
    assert math.isclose(mixer.get_effective_gain(), 0.2512, rel_tol=1e-3)

    ducked_gains = mixer.calculate_active_stem_gains()
    assert math.isclose(ducked_gains["combat"], 0.2512, rel_tol=1e-3)

    # Release ducking
    mixer.set_ducking(False)
    assert mixer.is_ducked is False
    assert mixer.get_effective_gain() == 1.0


# ---------------------------------------------------------------------------
# 4. Public HTTP Frontdoor API Tests
# ---------------------------------------------------------------------------


def test_soundscape_health_and_manifest(client: TestClient):
    """Verify healthz and microfrontend manifest frontdoors."""
    health_resp = client.get("/healthz")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"
    assert health_resp.json()["service"] == "soundscape"

    manifest_resp = client.get("/ui/manifest")
    assert manifest_resp.status_code == 200
    data = manifest_resp.json()
    assert data["service"] == "soundscape"
    assert data["package"] == "@runefoble/soundscape-ui"
    assert "runefoble-soundscape-controls" in data["components"]


def test_soundscape_stems_catalog(client: TestClient):
    """Verify GET /api/v1/soundscape/stems lists layers, weights, and presets."""
    resp = client.get("/api/v1/soundscape/stems?session_id=session-tomb-14")
    assert resp.status_code == 200
    data = resp.json()
    assert "ambient" in data["stem_layers"]
    assert "combat" in data["stem_layers"]
    assert "fireball" in data["foley_presets"]
    assert "sword_slash" in data["foley_presets"]


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

    # Read back current tension via GET
    get_resp = client.get("/api/v1/soundscape/tension?session_id=session-tomb-14")
    assert get_resp.status_code == 200
    status_data = get_resp.json()
    assert status_data["session_id"] == "session-tomb-14"
    assert status_data["tension_score"] == data["tension_score"]
    assert status_data["stem_profile"] == data["stem_profile"]


def test_dm_mood_override_and_ducking_frontdoor(client: TestClient):
    """Verify POST /override forces mood and POST /duck toggles -12dB attenuation."""
    override_payload = {
        "session_id": "session-tomb-14",
        "mood": "boss",
        "master_volume": 0.9,
    }
    resp = client.post("/api/v1/soundscape/override", json=override_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["stem_profile"] == "boss"
    assert data["manual_override"] is True
    assert data["override_mood"] == "boss"
    assert data["master_volume"] == 0.9

    # Toggle WebAudio ducking
    duck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={"session_id": "session-tomb-14", "is_ducked": True, "reason": "speech"},
    )
    assert duck_resp.status_code == 200
    duck_data = duck_resp.json()
    assert duck_data["is_ducked"] is True
    assert duck_data["attenuation_db"] == -12.0
    assert math.isclose(duck_data["effective_gain"], 0.9 * 0.2512, rel_tol=1e-3)


# ---------------------------------------------------------------------------
# 5. Event Bus Publishing & Reactive Subscription Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soundscape_event_bus_and_autonomous_reactivity():
    """Verify SoundscapeTrackChanged publication and reactivity to combat/speech events."""
    mock_redis = MockAsyncRedis()
    bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(bus)

    # 1. Incoming CombatEncounterStarted event
    combat_start_event = CombatEncounterStarted(
        aggregate_id=uuid4(),
        session_id="session-tomb-14",
        round_number=1,
        combatants=[{"name": "Goblin", "cr": 2.0}],
    )
    await handle_incoming_domain_event(combat_start_event)

    # Verify event published to Redis Stream
    stream_key = "runefoble.events.soundscape"
    assert stream_key in mock_redis.streams
    events_in_stream = mock_redis.streams[stream_key]
    assert len(events_in_stream) >= 1
    _, event_data = events_in_stream[-1]
    assert event_data["event_type"] == "runefoble.events.soundscape.track_changed"

    # 2. Incoming CombatRoundAdvanced event
    round_event = CombatRoundAdvanced(
        aggregate_id=uuid4(),
        session_id="session-tomb-14",
        round_number=3,
        active_combatant_id="comb-123",
    )
    await handle_incoming_domain_event(round_event)

    # 3. Incoming PlayerSpokeEvent -> triggers ducking
    session_uuid = uuid4()
    session_id_str = str(session_uuid)
    spoke_event = PlayerSpokeEvent(
        aggregate_id=uuid4(),
        session_id=session_uuid,
        speaker_id="player-valeros",
        speaker_name="Valeros",
        transcript="I ready my warhammer and charge the hobgoblin!",
    )
    await handle_incoming_domain_event(spoke_event)

    mixer = get_or_create_mixer(session_id_str)
    assert mixer.is_ducked is True
    assert mixer.get_effective_gain() < 0.5


# ---------------------------------------------------------------------------
# 6. SpiceDB Zanzibar Object-Level Authorization Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_soundscape_zanzibar_authorization(client: TestClient):
    """Verify Zanzibar authorization enforces caller permissions for DM mood override."""
    from soundscape.dependencies import get_spicedb_client

    # When SpiceDB denies permission:
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


# ---------------------------------------------------------------------------
# 7. Microfrontend & Lit Component File Invariants Tests
# ---------------------------------------------------------------------------


def test_soundscape_microfrontend_component_invariants():
    """Verify <runefoble-soundscape-controls> component, styles, and Storybook coverage."""
    ui_dir = REPO_ROOT / "services" / "soundscape" / "ui"
    comp_file = ui_dir / "src" / "runefoble-soundscape-controls.ts"
    styles_file = ui_dir / "src" / "runefoble-soundscape-controls.styles.ts"
    stories_file = ui_dir / "src" / "runefoble-soundscape-controls.stories.ts"

    assert comp_file.is_file()
    assert styles_file.is_file()
    assert stories_file.is_file()

    comp_content = comp_file.read_text(encoding="utf-8")
    styles_content = styles_file.read_text(encoding="utf-8")
    stories_content = stories_file.read_text(encoding="utf-8")

    # Hard Invariant 6: Decomposed files well under 500 lines
    assert len(comp_content.splitlines()) < 250
    assert len(styles_content.splitlines()) < 200
    assert len(stories_content.splitlines()) < 150

    # Custom element registration and custom events
    assert "@customElement('runefoble-soundscape-controls')" in comp_content
    assert "'soundscape-volume'" in comp_content
    assert "'soundscape-mood'" in comp_content
    assert "'soundscape-cue'" in comp_content
    assert "'soundscape-duck'" in comp_content

    # Bauhaus styling tokens
    assert "--rf-accent-primary" in styles_content
    assert "--rf-border-color" in styles_content
    assert "--rf-shadow" in styles_content

    # Storybook coverage
    assert "ExplorationDefault" in stories_content
    assert "CombatActive" in stories_content
    assert "BossClimax" in stories_content
    assert "VoiceDuckingActive" in stories_content
