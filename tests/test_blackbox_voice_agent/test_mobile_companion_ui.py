"""Blackbox TDD frontdoor tests for Mobile Companion UI Decomposition (TASK-0151).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Theming System and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines, all sub-files < 180 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from voice_agent.main import app as voice_app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def voice_client() -> TestClient:
    return TestClient(voice_app)


def test_voice_agent_manifest_exposes_decomposed_companion(voice_client: TestClient) -> None:
    """Verify GET /ui/manifest advertises mobile companion sub-components and styles."""
    resp = voice_client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "voice_agent"
    assert data["package"] == "@runefoble/voice-agent-ui"

    for comp in [
        "runefoble-mobile-companion",
        "audio-stream-controller",
        "haptic-ping-panel",
        "connection-status-badge",
    ]:
        assert comp in data["components"]
        assert comp in data["tags"]

    assert any("mobile_companion/styles" in s for s in data["styles"])

    # Manifest file matches runtime endpoint
    manifest_path = REPO_ROOT / "services/voice_agent/ui/manifest.json"
    assert manifest_path.is_file()
    file_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert file_data["components"] == data["components"]
    assert file_data["tags"] == data["tags"]


def test_mobile_companion_modular_file_limits() -> None:
    """Verify Hard Invariant 6 & DoD file limits strictly enforced."""
    limits = {
        "services/voice_agent/ui/src/runefoble-mobile-companion.ts": 180,
        "services/voice_agent/ui/src/runefoble-mobile-companion.styles.ts": 50,
        "services/voice_agent/ui/src/mobile_companion/audio_stream_controller.ts": 130,
        "services/voice_agent/ui/src/mobile_companion/haptic_ping_panel.ts": 120,
        "services/voice_agent/ui/src/mobile_companion/connection_status_badge.ts": 90,
        "services/voice_agent/ui/src/mobile_companion/styles/viewport.styles.ts": 110,
        "services/voice_agent/ui/src/mobile_companion/styles/badges.styles.ts": 110,
        "services/voice_agent/ui/src/mobile_companion/styles/audio.styles.ts": 110,
        "services/voice_agent/ui/src/mobile_companion/styles/whisper.styles.ts": 110,
        "services/voice_agent/ui/src/mobile_companion/styles/index.ts": 30,
        "services/voice_agent/ui/src/runefoble-mobile-companion.stories.ts": 180,
    }
    for rel_path, max_lines in limits.items():
        full_path = REPO_ROOT / rel_path
        assert full_path.is_file(), f"{full_path} must exist"
        lines = len(full_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{rel_path} has {lines} lines, exceeding target {max_lines}"
        assert lines < 180, f"{rel_path} has {lines} lines, exceeding strict DoD limit 180"


def test_mobile_companion_subcomponent_contracts() -> None:
    """Verify subcomponents, Custom Elements, and event contracts."""
    ui_src = REPO_ROOT / "services/voice_agent/ui/src"
    root_code = (ui_src / "runefoble-mobile-companion.ts").read_text(encoding="utf-8")
    audio_code = (ui_src / "mobile_companion/audio_stream_controller.ts").read_text(
        encoding="utf-8"
    )
    haptic_code = (ui_src / "mobile_companion/haptic_ping_panel.ts").read_text(encoding="utf-8")
    badge_code = (ui_src / "mobile_companion/connection_status_badge.ts").read_text(
        encoding="utf-8"
    )
    index_code = (ui_src / "index.ts").read_text(encoding="utf-8")

    # Custom element tags
    assert "@customElement('runefoble-mobile-companion')" in root_code
    assert "@customElement('audio-stream-controller')" in audio_code
    assert "@customElement('haptic-ping-panel')" in haptic_code
    assert "@customElement('connection-status-badge')" in badge_code

    # Exported in index
    assert "runefoble-mobile-companion" in index_code
    assert "mobile_companion/index.ts" in index_code

    # Subcomponent events
    assert "bitrate-change" in audio_code
    assert "mute-toggle" in audio_code
    assert "haptic-pulse" in haptic_code
    assert "whisper-blur-toggled" in haptic_code
    assert "whisper-dismissed" in haptic_code
    assert "turn-alert-dismissed" in haptic_code
    assert "reconnect" in badge_code


def test_mobile_companion_storybook_stories_coverage() -> None:
    """Verify Storybook stories include subcomponent coverage and root states."""
    stories_path = REPO_ROOT / "services/voice_agent/ui/src/runefoble-mobile-companion.stories.ts"
    assert stories_path.is_file()
    content = stories_path.read_text(encoding="utf-8")
    for story in [
        "DefaultConnected",
        "SecretWhisperActive",
        "ConstrainedCellularFallback",
        "TurnAlertPrompt",
        "OfflineDisconnected",
        "AudioStreamControllerStory",
        "HapticPingPanelStory",
        "ConnectionStatusBadgeStory",
        "InteractiveSimulator",
    ]:
        assert story in content, f"Story {story} missing from stories file"
