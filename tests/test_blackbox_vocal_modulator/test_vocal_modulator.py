"""Blackbox TDD frontdoor tests for DM Live Vocal Modulator and NPC Formant DSP Engine.

Governed by:
- ADR-0002: Event-Driven Watcher Gameplay Orchestration
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: Domain-Driven Design Architecture
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 1: SpiceDB Zanzibar Object-Level Authorization
- Hard Invariant 2: eventsource-py Declarative Aggregate & Domain Events
- Hard Invariant 6: File length limits
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import base64
import pathlib
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_events.vocal_dsp import (
    VocalModulatorPresetApplied,
    VocalModulatorPresetAppliedEvent,
    VoiceFilterToggled,
    VoiceFilterToggledEvent,
)
from voice_agent.audio_utils import generate_synthetic_audio
from voice_agent.coordinator import get_voice_room_coordinator
from voice_agent.main import app as voice_app

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def test_setup():
    coord = get_voice_room_coordinator()
    mock_spicedb = SpiceDBClient(use_mock=True)
    coord.set_spicedb(mock_spicedb)

    mock_bus = AsyncMock()
    coord.set_event_bus(mock_bus)

    client = TestClient(voice_app)
    return {
        "client": client,
        "coord": coord,
        "spicedb": mock_spicedb,
        "bus": mock_bus,
    }


@pytest.mark.asyncio
async def test_get_npc_voice_presets(test_setup):
    """Verify GET /voice/presets lists all available NPC creature presets."""
    client = test_setup["client"]
    resp = client.get("/voice/presets")
    assert resp.status_code == 200
    presets = resp.json()
    assert len(presets) >= 4

    preset_ids = {p["preset_id"] for p in presets}
    assert "ancient-dragon" in preset_ids
    assert "goblin-skulker" in preset_ids
    assert "celestial-spirit" in preset_ids
    assert "robotic-construct" in preset_ids

    # Also verify /api/v1/voice/presets alias
    alias_resp = client.get("/api/v1/voice/presets")
    assert alias_resp.status_code == 200
    assert alias_resp.json() == presets


@pytest.mark.asyncio
async def test_modulate_voice_with_synthetic_pcm_frames(test_setup):
    """Verify POST /voice/modulate applies DSP transformations to PCM audio under 50ms latency."""
    client = test_setup["client"]
    spicedb = test_setup["spicedb"]
    bus = test_setup["bus"]

    session_id = "test-session-dragon-01"
    user_id = "dm-evelyn"

    # Frontdoor Zanzibar authorization setup
    await spicedb.write_relationship("campaign", "camp-1", "dungeon_master", "user", user_id)
    await spicedb.write_relationship("session", session_id, "campaign", "campaign", "camp-1")

    # Generate synthetic PCM frame (50ms of audio = 800 samples @ 16kHz)
    input_pcm = generate_synthetic_audio(duration_sec=0.05, sample_rate=16000)
    input_b64 = base64.b64encode(input_pcm).decode("ascii")

    req_payload = {
        "session_id": session_id,
        "peer_id": "dm-speaker-1",
        "preset_name": "Ancient Dragon",
        "audio_base64": input_b64,
        "sample_rate": 16000,
        "enabled": True,
    }

    resp = client.post(
        "/voice/modulate",
        json=req_payload,
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["session_id"] == session_id
    assert data["preset_name"] == "Ancient Dragon"
    assert data["pitch_shift_semitones"] == -7.0
    assert data["formant_shift"] == 0.75
    assert data["resonance_hz"] == 140.0
    assert "sub_bass_resonance" in data["active_filters"]
    assert data["latency_ms"] < 50.0  # Latency benchmark requirement

    # Verify audio was modified by DSP filter chain
    out_b64 = data["audio_base64"]
    assert out_b64 is not None
    out_bytes = base64.b64decode(out_b64)
    assert len(out_bytes) == len(input_pcm)
    assert out_bytes != input_pcm

    # Verify event published to Redis event bus
    assert bus.publish_event.called
    events = [call.args[1] for call in bus.publish_event.call_args_list]
    preset_events = [e for e in events if isinstance(e, VocalModulatorPresetAppliedEvent)]
    assert len(preset_events) > 0
    event = preset_events[-1]
    assert event.preset_name == "Ancient Dragon"
    assert event.pitch_shift_semitones == -7.0


@pytest.mark.asyncio
async def test_modulate_all_creature_archetypes(test_setup):
    """Verify DSP transformations for Goblin, Celestial, and Robot archetypes."""
    client = test_setup["client"]
    spicedb = test_setup["spicedb"]
    session_id = "test-session-archetypes"
    user_id = "dm-evelyn"

    await spicedb.write_relationship("session", session_id, "control", "user", user_id)
    input_pcm = generate_synthetic_audio(duration_sec=0.04, sample_rate=16000)
    input_b64 = base64.b64encode(input_pcm).decode("ascii")

    archetypes = [
        ("Goblin Skulker", 6.5, 1.4, 2800.0),
        ("Celestial Spirit", 3.0, 1.2, 1600.0),
        ("Robotic Construct", -2.0, 0.95, 440.0),
    ]

    for name, expected_pitch, expected_formant, expected_res in archetypes:
        resp = client.post(
            "/voice/modulate",
            json={
                "session_id": session_id,
                "preset_name": name,
                "audio_base64": input_b64,
            },
            headers={"X-User-Id": user_id},
        )
        assert resp.status_code == 200
        d = resp.json()
        assert d["preset_name"] == name
        assert d["pitch_shift_semitones"] == expected_pitch
        assert d["formant_shift"] == expected_formant
        assert d["resonance_hz"] == expected_res
        assert d["latency_ms"] < 50.0
        out_pcm = base64.b64decode(d["audio_base64"])
        assert out_pcm != input_pcm


@pytest.mark.asyncio
async def test_modulate_custom_overrides_and_toggle(test_setup):
    """Verify fine-tuning pitch/formant parameters and toggling filter off."""
    client = test_setup["client"]
    spicedb = test_setup["spicedb"]
    bus = test_setup["bus"]
    session_id = "test-session-custom"
    user_id = "dm-evelyn"

    await spicedb.write_relationship("session", session_id, "control", "user", user_id)
    input_pcm = generate_synthetic_audio(duration_sec=0.03, sample_rate=16000)
    input_b64 = base64.b64encode(input_pcm).decode("ascii")

    # 1. Manual override without preset
    resp = client.post(
        "/voice/modulate",
        json={
            "session_id": session_id,
            "pitch_shift_semitones": -4.5,
            "formant_shift": 0.85,
            "resonance_hz": 220.0,
            "audio_base64": input_b64,
        },
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pitch_shift_semitones"] == -4.5
    assert data["formant_shift"] == 0.85
    assert data["resonance_hz"] == 220.0

    # 2. Toggle filter off (enabled=False)
    resp_off = client.post(
        "/voice/modulate",
        json={
            "session_id": session_id,
            "preset_name": "Ancient Dragon",
            "audio_base64": input_b64,
            "enabled": False,
        },
        headers={"X-User-Id": user_id},
    )
    assert resp_off.status_code == 200
    events = [call.args[1] for call in bus.publish_event.call_args_list]
    toggle_events = [e for e in events if isinstance(e, VoiceFilterToggledEvent)]
    assert len(toggle_events) > 0
    assert toggle_events[-1].enabled is False


@pytest.mark.asyncio
async def test_spicedb_zanzibar_authorization_enforcement(test_setup):
    """Verify object-level permission enforcement rejects unauthorized subjects (Hard Invariant 1)."""
    client = test_setup["client"]
    spicedb = test_setup["spicedb"]
    session_id = "secure-session-999"

    # Only DM Evelyn has permission
    await spicedb.write_relationship(
        "campaign", "camp-secure", "dungeon_master", "user", "dm-evelyn"
    )
    await spicedb.write_relationship("session", session_id, "campaign", "campaign", "camp-secure")

    # Unauthorized intruder attempts to modulate voice
    resp = client.post(
        "/voice/modulate",
        json={"session_id": session_id, "preset_name": "Ancient Dragon"},
        headers={"X-User-Id": "unauthorized-stranger"},
    )
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]

    # Authorized DM succeeds
    resp_auth = client.post(
        "/voice/modulate",
        json={"session_id": session_id, "preset_name": "Ancient Dragon"},
        headers={"X-User-Id": "dm-evelyn"},
    )
    assert resp_auth.status_code == 200


def test_vocal_modulator_error_handling(test_setup):
    """Verify 404 for unknown presets and 400 for malformed audio payloads."""
    client = test_setup["client"]
    spicedb = test_setup["spicedb"]
    session_id = "test-err-session"
    user_id = "dm-user"

    import asyncio

    asyncio.run(spicedb.write_relationship("session", session_id, "control", "user", user_id))

    # Unknown preset
    resp = client.post(
        "/voice/modulate",
        json={"session_id": session_id, "preset_name": "Nonexistent Gorgon"},
        headers={"X-User-Id": user_id},
    )
    assert resp.status_code == 404

    # Invalid base64 audio
    resp_bad = client.post(
        "/voice/modulate",
        json={
            "session_id": session_id,
            "preset_name": "Ancient Dragon",
            "audio_base64": "!!!not_valid_base64!!!",
        },
        headers={"X-User-Id": user_id},
    )
    assert resp_bad.status_code == 400


def test_modular_file_invariants():
    """Verify Hard Invariant 6: decomposed files strictly within length limits."""
    limits = {
        "services/voice_agent/src/voice_agent/dsp/formants.py": 160,
        "services/voice_agent/src/voice_agent/dsp/presets.py": 120,
        "services/voice_agent/src/voice_agent/dsp/pipeline.py": 140,
        "services/voice_agent/src/voice_agent/dsp/base.py": 170,
        "services/voice_agent/src/voice_agent/dsp/__init__.py": 170,
        "services/voice_agent/src/voice_agent/routers/vocal_effects.py": 160,
        "libs/runefoble_events/src/runefoble_events/vocal_dsp.py": 80,
    }

    for path_str, max_lines in limits.items():
        file_path = REPO_ROOT / path_str
        assert file_path.is_file(), f"File {path_str} does not exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines <= max_lines, f"{path_str} has {lines} lines (limit: {max_lines})"

    assert VocalModulatorPresetApplied is VocalModulatorPresetAppliedEvent
    assert VoiceFilterToggled is VoiceFilterToggledEvent
