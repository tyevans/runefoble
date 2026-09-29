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
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_events.vocal_dsp import VocalModulatorPresetAppliedEvent
from voice_agent.coordinator import get_voice_room_coordinator
from voice_agent.main import app as voice_app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def voice_client() -> TestClient:
    return TestClient(voice_app)


@pytest.fixture
def setup_coordinator():
    coord = get_voice_room_coordinator()
    mock_spicedb = MockSpiceDBClient()
    coord.set_spicedb(mock_spicedb)
    mock_bus = AsyncMock()
    coord.set_event_bus(mock_bus)
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


def test_vocal_modulator_file_length_invariants() -> None:
    """Verify Hard Invariant 6 & DoD file limits (<140 for modulator, <120 for sliders, <110 for styles)."""
    limits = {
        "services/voice_agent/ui/src/runefoble-vocal-modulator.ts": 140,
        "services/voice_agent/ui/src/runefoble-vocal-sliders.ts": 120,
        "services/voice_agent/ui/src/runefoble-vocal-modulator.styles.ts": 110,
        "services/voice_agent/ui/src/runefoble-vocal-modulator.stories.ts": 130,
        "tests/test_blackbox_vocal_modulator_ui/test_vocal_modulator_ui.py": 170,
    }
    for rel_path, max_lines in limits.items():
        full_path = REPO_ROOT / rel_path
        assert full_path.is_file(), f"{full_path} must exist"
        lines = len(full_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{rel_path} has {lines} lines, exceeding target {max_lines}"
        assert lines < 160 or rel_path.endswith(".py"), (
            f"{rel_path} has {lines} lines, exceeding strict DoD limit 160"
        )


def test_vocal_modulator_component_contracts() -> None:
    """Verify component and slider contracts, custom elements, and events."""
    ui_src = REPO_ROOT / "services/voice_agent/ui/src"
    mod_code = (ui_src / "runefoble-vocal-modulator.ts").read_text(encoding="utf-8")
    sliders_code = (ui_src / "runefoble-vocal-sliders.ts").read_text(encoding="utf-8")
    index_code = (ui_src / "index.ts").read_text(encoding="utf-8")

    assert "@customElement('runefoble-vocal-modulator')" in mod_code
    assert "@customElement('runefoble-vocal-sliders')" in sliders_code
    assert "runefoble-vocal-modulator" in index_code
    assert "runefoble-vocal-sliders" in index_code

    # Event dispatches & public control methods
    assert "vocal-modulate" in mod_code and "preset-select" in mod_code
    assert "vocal-param-change" in sliders_code
    assert "selectPreset" in mod_code and "toggleBypass" in mod_code
    assert "pitchShift" in sliders_code and "formantShift" in sliders_code


def test_vocal_modulator_storybook_stories_coverage() -> None:
    """Verify interactive Storybook stories cover all visual states."""
    stories_path = REPO_ROOT / "services/voice_agent/ui/src/runefoble-vocal-modulator.stories.ts"
    content = stories_path.read_text(encoding="utf-8")
    for story in [
        "DefaultBypassed",
        "DragonActive",
        "GoblinActive",
        "EtherealActive",
        "RoboticActive",
        "AdvancedSlidersOpen",
        "InteractiveSimulator",
    ]:
        assert story in content, f"Story {story} missing from stories file"


def test_app_shell_forwarding_export() -> None:
    """Verify App Shell forwarding export for runefoble-vocal-modulator."""
    shell_file = REPO_ROOT / "frontend/src/components/runefoble-vocal-modulator.ts"
    assert shell_file.is_file()
    assert "@runefoble/voice-agent-ui" in shell_file.read_text(encoding="utf-8")


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

    # Authorize session for DM user via SpiceDB
    spicedb, bus = setup_coordinator["spicedb"], setup_coordinator["bus"]
    session_id, user_id = "test-session-ui-mod", "dm_speaker"
    await spicedb.write_relationship("session", session_id, "control", "user", user_id)

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
        headers={"X-User-Id": user_id},
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
