"""Blackbox TDD test suite for Soundscape Transitions & Ducking (TASK-0095).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Tests audio stem mixing, track crossfading, WebAudio -12dB voice ducking,
manual mood override frontdoors, and Lit microfrontend UI component invariants.
"""

from __future__ import annotations

import math
from uuid import uuid4

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_events import (
    PlayerSpokeEvent,
    SoundscapeDuckingToggled,
    SoundscapeTrackChanged,
)
from soundscape.dependencies import (
    get_or_create_mixer,
    handle_incoming_domain_event,
    reset_dependencies,
)
from soundscape.main import app
from soundscape.mixer import DUCKING_ATTENUATION_DB, DUCKING_LINEAR_MULTIPLIER, AudioStemMixer

from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.fixture
def tomb_session_id(trusted_ws_issuer) -> str:
    """Create a campaign and a session through the gateway frontdoor. The default test subject owns both."""
    gateway = TestClient(gateway_app)
    campaign = gateway.post(
        "/api/v1/campaigns",
        json={"title": "Tomb of Echoes", "setting": "Underdark"},
        headers=auth_headers("soundscape-tester"),
    )
    assert campaign.status_code == 201, campaign.text
    session = gateway.post(
        f"/api/v1/campaigns/{campaign.json()['id']}/sessions",
        json={"title": "Echoing Depths"},
        headers=auth_headers("soundscape-tester"),
    )
    assert session.status_code == 201, session.text
    return session.json()["id"]


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture(autouse=True)
def clean_environment():
    """Ensure clean aggregate, mixer, and bus states before and after each test."""
    reset_dependencies()
    yield
    reset_dependencies()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, headers=auth_headers("soundscape-tester"))


def test_soundscape_transition_cloudevents_registration():
    """Verify soundscape track and ducking domain events register with CloudEvents."""
    track_cls = get_event_class_or_none("runefoble.events.soundscape.track_changed")
    assert track_cls is not None
    assert track_cls is SoundscapeTrackChanged

    duck_cls = get_event_class_or_none("runefoble.events.soundscape.ducking_toggled")
    assert duck_cls is not None
    assert duck_cls is SoundscapeDuckingToggled

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


def test_stem_mixer_attenuation_and_ducking():
    """Verify stem weights and -12dB ducking calculation (PRD-0010, US-0039)."""
    mixer = AudioStemMixer(stem_profile="combat", master_volume=1.0)
    gains = mixer.calculate_active_stem_gains()
    assert gains["combat"] == 1.0
    assert gains["boss"] == 0.2

    # Ducking attenuation: -12 dB = 10^(-12/20) ~ 0.2512
    assert DUCKING_ATTENUATION_DB == -12.0
    assert math.isclose(DUCKING_LINEAR_MULTIPLIER, 0.251188, rel_tol=1e-3)

    mixer.set_ducking(True, reason="speech")
    assert mixer.is_ducked is True
    assert math.isclose(mixer.get_effective_gain(), 0.2512, rel_tol=1e-3)

    ducked_gains = mixer.calculate_active_stem_gains()
    assert math.isclose(ducked_gains["combat"], 0.2512, rel_tol=1e-3)

    mixer.set_ducking(False)
    assert mixer.is_ducked is False
    assert mixer.get_effective_gain() == 1.0


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


def test_dm_mood_override_and_ducking_frontdoor(client: TestClient, tomb_session_id: str):
    """Verify POST /override forces mood and POST /duck toggles -12dB attenuation."""
    override_payload = {
        "session_id": tomb_session_id,
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

    duck_resp = client.post(
        "/api/v1/soundscape/duck",
        json={"session_id": tomb_session_id, "is_ducked": True, "reason": "speech"},
    )
    assert duck_resp.status_code == 200
    duck_data = duck_resp.json()
    assert duck_data["is_ducked"] is True
    assert duck_data["attenuation_db"] == -12.0
    assert math.isclose(duck_data["effective_gain"], 0.9 * 0.2512, rel_tol=1e-3)


@pytest.mark.asyncio
async def test_voice_ducking_reactive_subscription():
    """Verify incoming PlayerSpokeEvent triggers automatic voice ducking."""
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
