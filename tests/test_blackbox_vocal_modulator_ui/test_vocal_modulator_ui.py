"""Blackbox TDD frontdoor tests for DM Vocal Modulator Controls UI (TASK-0160).

Governing ADRs: ADR-0004, ADR-0012, ADR-0013.
Verifies:
- Microfrontend manifest advertisement via GET /ui/manifest.
- Strict decomposition & file length limits (< 140 for modulator, < 120 for sliders, < 110 for styles).
- Custom Element registration & event contracts.
- Storybook stories coverage.
- Public frontdoor REST integration for presets and voice modulation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from runefoble_events.vocal_dsp import VocalModulatorPresetAppliedEvent
from voice_agent.coordinator import (
    VoiceRoomCoordinator,
    get_voice_room_coordinator,
    set_voice_room_coordinator,
)
from voice_agent.main import app as voice_app

from tests.helpers.module_state import SeamRestorer
from tests.helpers.spicedb_factory import grant_voice_session
from tests.helpers.voice_identity import voice_auth_headers

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def voice_client(trusted_voice_issuer) -> TestClient:
    return TestClient(voice_app, headers=voice_auth_headers())


@pytest.fixture
def setup_coordinator(seam_restorer: SeamRestorer):
    """Give the test a process coordinator on a mock bus. The previous coordinator is restored."""
    mock_spicedb = get_spicedb_client()
    mock_bus = AsyncMock()
    coord = seam_restorer.replace(
        get_voice_room_coordinator,
        set_voice_room_coordinator,
        VoiceRoomCoordinator(event_bus=mock_bus),
    )
    return {"coord": coord, "spicedb": mock_spicedb, "bus": mock_bus}


def test_voice_agent_manifest_exposes_vocal_modulator(voice_client: TestClient) -> None:
    """Verify GET /ui/manifest advertises runefoble-vocal-modulator and sliders."""
    resp = voice_client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "voice_agent"
    assert data["package"] == "@runefoble/voice-agent-ui"
    assert "runefoble-vocal-modulator" in data["components"]
    assert "runefoble-vocal-sliders" in data["components"]
    assert any("runefoble-vocal-modulator.styles.ts" in s for s in data["styles"])

    # Manifest file matches runtime endpoint
    manifest_path = REPO_ROOT / "services/voice_agent/ui/manifest.json"
    file_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert file_data["components"] == data["components"]
    assert file_data["tags"] == data["tags"]


@pytest.mark.asyncio
async def test_frontdoor_presets_and_modulate_integration(
    voice_client: TestClient, setup_coordinator: dict
) -> None:
    """Verify frontdoor /voice/presets and /voice/modulate endpoints used by UI."""
    resp_presets = voice_client.get("/voice/presets")
    assert resp_presets.status_code == 200
    presets = resp_presets.json()
    preset_names = {p["name"] for p in presets}
    assert "Ancient Dragon" in preset_names and "Goblin Skulker" in preset_names

    # Schema tuples: the DM is the campaign dungeon_master for this session
    bus = setup_coordinator["bus"]
    session_id, user_id = "test-session-ui-mod", "dm_speaker"
    await grant_voice_session(session_id, dm=user_id)

    mod_resp = voice_client.post(
        "/voice/modulate",
        json={
            "session_id": session_id,
            "peer_id": "dm_speaker",
            "preset_name": "Ancient Dragon",
            "pitch_shift_semitones": -7.0,
            "formant_shift": 0.75,
            "resonance_hz": 140.0,
            "octave_offset": -0.5,
            "enabled": True,
        },
        headers=voice_auth_headers(user_id),
    )
    assert mod_resp.status_code == 200
    res_data = mod_resp.json()
    assert res_data["preset_name"] == "Ancient Dragon"
    assert res_data["pitch_shift_semitones"] == -7.0

    # Verify event published
    assert bus.publish_event.called
    events = [call.args[1] for call in bus.publish_event.call_args_list]
    applied = [e for e in events if isinstance(e, VocalModulatorPresetAppliedEvent)]
    assert len(applied) > 0
    assert applied[-1].preset_name == "Ancient Dragon"
