"""Blackbox tests for Microfrontend Architecture and Service Component Vendoring (TASK-0024).

Verifies that each service bounded context vendors its own UI components, exposes
its microfrontend manifest through its public HTTP frontdoor, and that the App Shell
orchestrates all microfrontends.
"""

from pathlib import Path

import pytest
from starlette.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def board_client():
    from board_state.main import app

    return TestClient(app)


@pytest.fixture
def character_client():
    from character_sheet.main import app

    return TestClient(app)


@pytest.fixture
def session_client():
    from game_session.main import app

    return TestClient(app)


@pytest.fixture
def watcher_client():
    from the_watcher.main import app

    return TestClient(app)


@pytest.fixture
def voice_client():
    from voice_agent.main import app

    return TestClient(app)


def test_board_state_ui_manifest_frontdoor(board_client):
    """Verify board_state service vendors its microfrontend via GET /ui/manifest."""
    response = board_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "board_state"
    assert data["package"] == "@runefoble/board-state-ui"
    assert "runefoble-board" in data["components"]


def test_character_sheet_ui_manifest_frontdoor(character_client):
    """Verify character_sheet service vendors its microfrontend via GET /ui/manifest."""
    response = character_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "character_sheet"
    assert data["package"] == "@runefoble/character-sheet-ui"
    assert "runefoble-character-card" in data["components"]
    assert "runefoble-absentee-recap" in data["components"]


def test_game_session_ui_manifest_frontdoor(session_client):
    """Verify game_session service vendors its microfrontend via GET /ui/manifest."""
    response = session_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "game_session"
    assert data["package"] == "@runefoble/game-session-ui"
    assert "runefoble-initiative-tracker" in data["components"]
    assert "runefoble-dice-roller" in data["components"]
    assert "runefoble-spectator-view" in data["components"]


def test_the_watcher_ui_manifest_frontdoor(watcher_client):
    """Verify the_watcher service vendors its microfrontend via GET /ui/manifest."""
    response = watcher_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "the_watcher"
    assert data["package"] == "@runefoble/the-watcher-ui"
    assert "runefoble-watcher-feed" in data["components"]
    assert "runefoble-autonomous-dm" in data["components"]


def test_voice_agent_ui_manifest_frontdoor(voice_client):
    """Verify voice_agent service vendors its microfrontend via GET /ui/manifest."""
    response = voice_client.get("/ui/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "voice_agent"
    assert data["package"] == "@runefoble/voice-agent-ui"
    assert "runefoble-voice-controls" in data["components"]


def test_service_ui_package_integrity():
    """Verify that all service UI packages have package.json, tsconfig.json, and Lit elements."""
    expected_packages = [
        ("services/board_state/ui", "@runefoble/board-state-ui", "runefoble-board"),
        (
            "services/character_sheet/ui",
            "@runefoble/character-sheet-ui",
            "runefoble-character-card",
        ),
        ("services/game_session/ui", "@runefoble/game-session-ui", "runefoble-initiative-tracker"),
        ("services/the_watcher/ui", "@runefoble/the-watcher-ui", "runefoble-watcher-feed"),
        ("services/voice_agent/ui", "@runefoble/voice-agent-ui", "runefoble-voice-controls"),
    ]

    for rel_dir, pkg_name, elem_tag in expected_packages:
        pkg_path = REPO_ROOT / rel_dir / "package.json"
        assert pkg_path.is_file(), f"{pkg_path} must exist"
        content = pkg_path.read_text(encoding="utf-8")
        assert f'"name": "{pkg_name}"' in content

        tsconfig = REPO_ROOT / rel_dir / "tsconfig.json"
        assert tsconfig.is_file(), f"{tsconfig} must exist"

        index_file = REPO_ROOT / rel_dir / "src" / "index.ts"
        assert index_file.is_file(), f"{index_file} must exist"

        src_files = list((REPO_ROOT / rel_dir / "src").glob("*.ts"))
        assert any(
            f"@customElement('{elem_tag}')" in f.read_text(encoding="utf-8") for f in src_files
        ), f"Custom element '{elem_tag}' not found in {rel_dir}/src"


def test_app_shell_microfrontend_composition():
    """Verify frontend/src/runefoble-app.ts acts as the App Shell orchestrating microfrontends."""
    shell_file = REPO_ROOT / "frontend" / "src" / "runefoble-app.ts"
    assert shell_file.is_file()
    content = shell_file.read_text(encoding="utf-8")

    # Shell imports all microfrontend packages
    assert "@runefoble/board-state-ui" in content
    assert "@runefoble/character-sheet-ui" in content
    assert "@runefoble/game-session-ui" in content
    assert "@runefoble/the-watcher-ui" in content
    assert "@runefoble/voice-agent-ui" in content

    # Shell composes elements into the DOM
    assert "<runefoble-board" in content
    assert "<runefoble-character-card" in content
    assert "<runefoble-watcher-feed" in content
    assert "<runefoble-voice-controls" in content
    assert "<runefoble-theme-switcher" in content


def test_monorepo_pnpm_workspace_declaration():
    """Verify root pnpm-workspace.yaml links the app shell and service microfrontends."""
    workspace_file = REPO_ROOT / "pnpm-workspace.yaml"
    assert workspace_file.is_file()
    content = workspace_file.read_text(encoding="utf-8")
    assert "frontend" in content
    assert "services/*/ui" in content


def test_storybook_aggregates_service_stories():
    """Verify Storybook main.ts is configured to discover all microfrontend stories."""
    sb_main = REPO_ROOT / "frontend" / ".storybook" / "main.ts"
    assert sb_main.is_file()
    content = sb_main.read_text(encoding="utf-8")
    assert "services/*/ui/src/**/*.stories" in content


def test_voice_controls_visualizer_and_webrtc_spec():
    """Verify runefoble-voice-controls implements WebAudio AnalyserNode visualizer & WebRTC monitor."""
    ui_src = REPO_ROOT / "services" / "voice_agent" / "ui" / "src"
    voice_ctrl_file = ui_src / "runefoble-voice-controls.ts"
    assert voice_ctrl_file.is_file()
    content = voice_ctrl_file.read_text(encoding="utf-8")

    # Custom element registration
    assert "@customElement('runefoble-voice-controls')" in content

    # Component properties
    assert "isListening" in content
    assert "connectionState" in content
    assert "bandwidthQuality" in content
    assert "bitrateKbps" in content
    assert "packetsLost" in content
    assert "latencyMs" in content
    assert "activeFilters" in content

    # CustomEvents dispatched
    assert "'voice-toggle'" in content
    assert "'voice-state'" in content
    assert "'voice-level'" in content

    # WebAudio & Canvas visualizer
    assert "waveform-canvas" in content
    assert "AnalyserNode" in content
    assert "AudioContext" in content
    assert "renderWaveform" in content

    # WebRTC monitor UI elements
    assert "badge-webrtc" in content
    assert "badge-warning" in content
    assert "badge-dsp" in content

    # Bauhaus styling tokens
    assert "--rf-accent-primary" in content
    assert "--rf-shadow" in content
    assert "--rf-border-color" in content


def test_voice_controls_storybook_stories_coverage():
    """Verify Storybook stories cover inactive, active waveform, low bandwidth, and DSP afflictions."""
    stories_file = (
        REPO_ROOT
        / "services"
        / "voice_agent"
        / "ui"
        / "src"
        / "runefoble-voice-controls.stories.ts"
    )
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")

    assert "DefaultMuted" in content
    assert "Inactive" in content
    assert "WaveformActive" in content
    assert "LowBandwidthWarning" in content
    assert "AfflictionDspActive" in content
