"""Blackbox TDD frontdoor test suite for Character Leitmotifs & Adaptive Signatures (TASK-0102).

Governed by:
- ADR-0002, ADR-0006, ADR-0010, ADR-0013
- Hard Invariant 1 (SpiceDB Zanzibar), Hard Invariant 2 (eventsource-py)
- Hard Invariant 6 (File length < 500 lines), Hard Invariant 7 (Blackbox TDD with Frontdoor Setup)
- PRD-0016 & US-0046 (Character Leitmotifs and Dynamic Theme Scoring)
"""

from __future__ import annotations

import math
from pathlib import Path
from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_events import (
    CriticalHitRolled,
    CriticalHitScored,
    DeathSaveStarted,
    DiceRolled,
    LeitmotifProfileConfigured,
    LeitmotifTriggered,
    PlayerSpokeEvent,
)
from runefoble_platform.bus import bus as platform_bus
from soundscape.dependencies import (
    get_or_create_leitmotif_engine,
    handle_incoming_domain_event,
    reset_dependencies,
    set_spicedb_client,
)
from soundscape.leitmotif import calculate_envelope_gain
from soundscape.main import app
from soundscape.mixer import DUCKING_ATTENUATION_DB, DUCKING_LINEAR_MULTIPLIER

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean aggregate, mixer, bus, and authorization state for each test."""
    mock_db = MockSpiceDBClient()
    set_spicedb_client(mock_db)
    reset_dependencies()
    yield
    reset_dependencies()
    mock_db._tuples.clear()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_leitmotif_cloudevents_registration() -> None:
    """Verify leitmotif and combat trigger domain events register with CloudEvents."""
    profile_cls = get_event_class_or_none("runefoble.events.soundscape.leitmotif_configured")
    assert profile_cls is not None
    assert profile_cls is LeitmotifProfileConfigured

    triggered_cls = get_event_class_or_none("runefoble.events.soundscape.leitmotif_triggered")
    assert triggered_cls is not None
    assert triggered_cls is LeitmotifTriggered

    crit_cls = get_event_class_or_none("runefoble.events.character.critical_hit_scored")
    assert crit_cls is not None
    assert crit_cls is CriticalHitScored
    assert CriticalHitRolled is CriticalHitScored

    death_cls = get_event_class_or_none("runefoble.events.character.death_save_started")
    assert death_cls is not None
    assert death_cls is DeathSaveStarted

    event = LeitmotifTriggered(
        session_id="session-tomb-14",
        character_id="char-nadia",
        character_name="Nadia",
        motif_type="triumphant",
        instrument_timbre="lute",
        stem_url="http://silo:9000/runefoble-assets/audio/leitmotif/lute_triumphant.ogg",
        tempo_multiplier=1.05,
        volume_gain=1.0,
        trigger_reason="critical_hit",
    )
    ce = event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.soundscape.leitmotif_triggered"
    assert ce["data"]["character_id"] == "char-nadia"
    assert ce["data"]["motif_type"] == "triumphant"
    assert ce["data"]["instrument_timbre"] == "lute"


def test_list_timbre_presets_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/soundscape/leitmotif/timbres returns available presets."""
    resp = client.get("/api/v1/soundscape/leitmotif/timbres")
    assert resp.status_code == 200
    data = resp.json()
    assert "presets" in data
    assert "supported_timbres" in data
    assert "lute" in data["supported_timbres"]
    assert "brass" in data["supported_timbres"]
    assert "woodwind" in data["supported_timbres"]
    assert "strings" in data["supported_timbres"]
    assert "synth" in data["supported_timbres"]

    lute_preset = data["presets"]["lute"]
    assert "triumphant_stem_url" in lute_preset
    assert "somber_stem_url" in lute_preset
    assert lute_preset["label"] == "Lute & Celtic Flute"


def test_character_leitmotif_profile_crud_frontdoor(client: TestClient) -> None:
    """Verify POST and GET /api/v1/soundscape/leitmotif/profile endpoints."""
    payload = {
        "session_id": "session-tomb-14",
        "character_id": "char-nadia",
        "character_name": "Nadia",
        "instrument_timbre": "lute",
        "tempo_multiplier": 1.05,
        "volume_gain": 1.0,
        "attack_ms": 120,
        "release_ms": 300,
        "duration_ms": 4000,
    }
    resp = client.post("/api/v1/soundscape/leitmotif/profile", json=payload)
    assert resp.status_code == 200
    created = resp.json()
    assert created["character_id"] == "char-nadia"
    assert created["instrument_timbre"] == "lute"
    assert created["tempo_multiplier"] == 1.05
    assert "lute_triumphant.ogg" in created["triumphant_stem_url"]
    assert "lute_somber.ogg" in created["somber_stem_url"]

    get_resp = client.get(
        "/api/v1/soundscape/leitmotif/profile/char-nadia?session_id=session-tomb-14"
    )
    assert get_resp.status_code == 200
    retrieved = get_resp.json()
    assert retrieved["character_name"] == "Nadia"
    assert retrieved["attack_ms"] == 120


def test_trigger_and_audition_leitmotif_frontdoor(client: TestClient) -> None:
    """Verify POST /api/v1/soundscape/leitmotif/trigger stinger audition."""
    client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json={
            "session_id": "session-tomb-14",
            "character_id": "char-valeros",
            "character_name": "Valeros",
            "instrument_timbre": "brass",
            "tempo_multiplier": 1.0,
        },
    )
    trigger_resp = client.post(
        "/api/v1/soundscape/leitmotif/trigger",
        json={
            "session_id": "session-tomb-14",
            "character_id": "char-valeros",
            "motif_type": "triumphant",
            "trigger_reason": "audition",
        },
    )
    assert trigger_resp.status_code == 200
    playback = trigger_resp.json()
    assert playback["character_id"] == "char-valeros"
    assert playback["motif_type"] == "triumphant"
    assert playback["instrument_timbre"] == "brass"
    assert playback["scheduled_latency_ms"] <= 250
    assert playback["is_ducked"] is False

    active_resp = client.get("/api/v1/soundscape/leitmotif/active?session_id=session-tomb-14")
    assert active_resp.status_code == 200
    active_data = active_resp.json()
    assert active_data["is_playing"] is True
    assert active_data["active_leitmotif"]["character_id"] == "char-valeros"


@pytest.mark.asyncio
async def test_clutch_critical_hit_triggers_triumphant_leitmotif(client: TestClient) -> None:
    """Scenario 1: Clutch Critical Hit Theme Stinger within 250ms (US-0046)."""
    client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json={
            "session_id": "session-tomb-14",
            "character_id": "char-nadia",
            "character_name": "Nadia",
            "instrument_timbre": "lute",
            "tempo_multiplier": 1.05,
        },
    )
    captured_events: list[LeitmotifTriggered] = []

    async def on_event(ev: LeitmotifTriggered) -> None:
        captured_events.append(ev)

    platform_bus.subscribe("runefoble.events.soundscape.leitmotif_triggered", on_event)

    crit_event = CriticalHitScored(
        session_id="session-tomb-14",
        character_id="char-nadia",
        character_name="Nadia",
        roll_total=20,
    )
    await handle_incoming_domain_event(crit_event)

    engine = get_or_create_leitmotif_engine("session-tomb-14")
    playback = engine.get_active_status()
    assert playback is not None
    assert playback.character_id == "char-nadia"
    assert playback.motif_type == "triumphant"
    assert playback.instrument_timbre == "lute"
    assert playback.scheduled_latency_ms <= 250
    assert "lute_triumphant.ogg" in playback.stem_url

    assert len(captured_events) == 1
    assert captured_events[0].character_id == "char-nadia"
    assert captured_events[0].motif_type == "triumphant"
    assert captured_events[0].trigger_reason == "critical_hit"


@pytest.mark.asyncio
async def test_dice_rolled_crit_triggers_triumphant_stinger() -> None:
    """Verify DiceRolled with is_crit=True reactively triggers leitmotif stinger."""
    dice_event = DiceRolled(
        session_id="session-tomb-14",
        roller_id="char-nadia",
        roller_name="Nadia",
        formula="1d20+5",
        total=25,
        rolls=[20],
        is_crit=True,
    )
    await handle_incoming_domain_event(dice_event)

    engine = get_or_create_leitmotif_engine("session-tomb-14")
    playback = engine.get_active_status()
    assert playback is not None
    assert playback.character_id == "char-nadia"
    assert playback.motif_type == "triumphant"


@pytest.mark.asyncio
async def test_near_death_triggers_somber_cello_leitmotif(client: TestClient) -> None:
    """Scenario 2: Near-Death Tension & Somber Theme on DeathSaveStarted (US-0046)."""
    client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json={
            "session_id": "session-tomb-14",
            "character_id": "char-kyra",
            "character_name": "Kyra",
            "instrument_timbre": "strings",
            "tempo_multiplier": 0.95,
        },
    )
    death_event = DeathSaveStarted(
        session_id="session-tomb-14",
        character_id="char-kyra",
        character_name="Kyra",
        current_hp=0,
    )
    await handle_incoming_domain_event(death_event)

    engine = get_or_create_leitmotif_engine("session-tomb-14")
    playback = engine.get_active_status()
    assert playback is not None
    assert playback.character_id == "char-kyra"
    assert playback.motif_type == "somber"
    assert playback.instrument_timbre == "strings"
    assert "strings_somber.ogg" in playback.stem_url


@pytest.mark.asyncio
async def test_automatic_voice_ducking_attenuates_leitmotif_by_12db(client: TestClient) -> None:
    """Verify WebAudio sidechain compressor applies -12dB attenuation during voice activity."""
    session_uuid = uuid4()
    session_id_str = str(session_uuid)
    client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json={
            "session_id": session_id_str,
            "character_id": "char-nadia",
            "character_name": "Nadia",
            "instrument_timbre": "lute",
            "volume_gain": 1.0,
        },
    )
    client.post(
        "/api/v1/soundscape/leitmotif/trigger",
        json={
            "session_id": session_id_str,
            "character_id": "char-nadia",
            "motif_type": "triumphant",
        },
    )

    engine = get_or_create_leitmotif_engine(session_id_str)
    status_before = engine.get_active_status()
    assert status_before is not None
    assert status_before.is_ducked is False
    assert status_before.effective_gain == 1.0

    spoke_event = PlayerSpokeEvent(
        aggregate_id=uuid4(),
        session_id=session_uuid,
        speaker_id="player-marcus",
        speaker_name="Marcus",
        transcript="Nadia, incredible shot!",
    )
    await handle_incoming_domain_event(spoke_event)

    status_ducked = engine.get_active_status()
    assert status_ducked is not None
    assert status_ducked.is_ducked is True
    assert status_ducked.ducking_attenuation_db == DUCKING_ATTENUATION_DB
    assert math.isclose(status_ducked.effective_gain, DUCKING_LINEAR_MULTIPLIER, rel_tol=1e-3)

    duck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={"session_id": session_id_str, "is_ducked": False, "reason": "none"},
    )
    assert duck_resp.status_code == 200

    engine.set_ducking(False)
    status_restored = engine.get_active_status()
    assert status_restored is not None
    assert status_restored.is_ducked is False
    assert status_restored.effective_gain == 1.0


def test_volume_envelope_ramps_and_stage_transitions() -> None:
    """Verify smooth attack, sustain, and release envelope calculations without clipping."""
    attack_ms, release_ms, duration_ms = 150, 350, 4000

    gain_start, stage_start = calculate_envelope_gain(0, attack_ms, release_ms, duration_ms)
    assert gain_start == 0.0
    assert stage_start == "attack"

    gain_attack, stage_attack = calculate_envelope_gain(75, attack_ms, release_ms, duration_ms)
    assert math.isclose(gain_attack, 0.5, rel_tol=1e-2)
    assert stage_attack == "attack"

    gain_sustain, stage_sustain = calculate_envelope_gain(2000, attack_ms, release_ms, duration_ms)
    assert gain_sustain == 1.0
    assert stage_sustain == "sustain"

    gain_release, stage_release = calculate_envelope_gain(3825, attack_ms, release_ms, duration_ms)
    assert math.isclose(gain_release, 0.5, rel_tol=1e-2)
    assert stage_release == "release"

    gain_decay, stage_decay = calculate_envelope_gain(4100, attack_ms, release_ms, duration_ms)
    assert gain_decay == 0.0
    assert stage_decay == "decay"


@pytest.mark.asyncio
async def test_zanzibar_authorization_enforced_on_leitmotif_profile(client: TestClient) -> None:
    """Verify unauthorized users receive 403 Forbidden under Zanzibar schema."""
    mock_spicedb = MockSpiceDBClient()
    set_spicedb_client(mock_spicedb)

    payload = {
        "session_id": "session-tomb-14",
        "character_id": "char-restricted",
        "character_name": "Restricted Char",
        "instrument_timbre": "brass",
    }
    resp_forbidden = client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json=payload,
        headers={"x-user-id": "user-unauthorized"},
    )
    assert resp_forbidden.status_code == 403
    assert "Forbidden" in resp_forbidden.json()["detail"]

    await mock_spicedb.write_relationship(
        resource_type="character",
        resource_id="char-restricted",
        relation="owner",
        subject_type="user",
        subject_id="user-owner",
    )
    resp_allowed = client.post(
        "/api/v1/soundscape/leitmotif/profile",
        json=payload,
        headers={"x-user-id": "user-owner"},
    )
    assert resp_allowed.status_code == 200
    assert resp_allowed.json()["character_id"] == "char-restricted"


def test_soundscape_manifest_includes_leitmotif_config(client: TestClient) -> None:
    """Verify GET /ui/manifest advertises runefoble-leitmotif-config."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert "runefoble-leitmotif-config" in data["components"]
    assert "runefoble-leitmotif-config" in data["tags"]
    assert any("runefoble-leitmotif-config.styles" in s for s in data["styles"])


def test_leitmotif_microfrontend_component_invariants() -> None:
    """Verify Lit component, styles, and Storybook stories conform to code limits."""
    ui_dir = REPO_ROOT / "services" / "soundscape" / "ui"
    comp_file = ui_dir / "src" / "runefoble-leitmotif-config.ts"
    styles_file = ui_dir / "src" / "runefoble-leitmotif-config.styles.ts"
    stories_file = ui_dir / "src" / "runefoble-leitmotif-config.stories.ts"

    assert comp_file.is_file()
    assert styles_file.is_file()
    assert stories_file.is_file()

    comp_content = comp_file.read_text(encoding="utf-8")
    styles_content = styles_file.read_text(encoding="utf-8")
    stories_content = stories_file.read_text(encoding="utf-8")

    assert len(comp_content.splitlines()) < 300
    assert len(styles_content.splitlines()) < 250
    assert len(stories_content.splitlines()) < 200

    assert "@customElement('runefoble-leitmotif-config')" in comp_content
    assert "'leitmotif-audition'" in comp_content
    assert "'leitmotif-configured'" in comp_content
    assert "'leitmotif-timbre-selected'" in comp_content

    assert "--rf-accent-primary" in styles_content
    assert "--rf-border-color" in styles_content
    assert "--rf-shadow" in styles_content

    assert "DefaultNadiaLute" in stories_content
    assert "HeroicBrass" in stories_content
    assert "SomberCelloStrings" in stories_content
    assert "VoiceDuckingActive" in stories_content
