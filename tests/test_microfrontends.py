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
    assert "runefoble-map-uploader" in data["components"]


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
        ("services/board_state/ui", "@runefoble/board-state-ui", "runefoble-map-uploader"),
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
    assert "<runefoble-settings-modal" in content


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

    # Bauhaus styling tokens (checked in component and its companion styles)
    styles_file = ui_src / "runefoble-voice-controls.styles.ts"
    styles_content = styles_file.read_text(encoding="utf-8") if styles_file.is_file() else ""
    full_content = content + "\n" + styles_content
    assert "--rf-accent-primary" in full_content
    assert "--rf-shadow" in full_content
    assert "--rf-border-color" in full_content


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


def test_battlemap_uploader_microfrontend_frontdoor(board_client):
    """Verify battlemap asset uploader component integrity and Silo S3 upload frontdoor."""
    from gateway_api.main import app as gateway_app

    # 1. Manifest discovery frontdoor
    response = board_client.get("/ui/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["service"] == "board_state"
    assert manifest["package"] == "@runefoble/board-state-ui"
    assert "runefoble-map-uploader" in manifest["components"]

    # 2. Silo S3 asset upload frontdoor integration
    gateway_client = TestClient(gateway_app)
    sample_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
        b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    upload_res = gateway_client.post(
        "/api/v1/assets/upload",
        files={"file": ("crypt_dungeon_grid.png", sample_png, "image/png")},
        data={"owner_id": "gm-alex", "asset_type": "battlemap"},
    )
    assert upload_res.status_code == 200
    upload_data = upload_res.json()
    assert "asset_id" in upload_data
    assert "battlemaps/" in upload_data["object_key"]
    assert upload_data["content_type"] == "image/png"
    assert upload_data["owner_id"] == "gm-alex"
    assert "download_url" in upload_data

    # 3. Component code and event contract verification
    comp_file = REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-map-uploader.ts"
    assert comp_file.is_file()
    code = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-map-uploader')" in code
    assert "map-uploaded" in code
    assert "shroud-overlay" in code
    assert "uploadEndpoint" in code

    # 4. Interactive Storybook stories contract
    stories_file = (
        REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-map-uploader.stories.ts"
    )
    assert stories_file.is_file()
    stories_code = stories_file.read_text(encoding="utf-8")
    assert "EmptyDropzone" in stories_code
    assert "UploadingProgress" in stories_code
    assert "AlignedMapPreview" in stories_code
    assert "FogOfWarMasked" in stories_code


def test_microfrontend_component_styles_and_subview_decomposition_integrity():
    """Verify TASK-0043: CSS styles extracted to *.styles.ts companion modules and file length limits."""
    decomposed_targets = [
        {
            "component": REPO_ROOT
            / "services"
            / "game_session"
            / "ui"
            / "src"
            / "runefoble-initiative-tracker.ts",
            "styles": REPO_ROOT
            / "services"
            / "game_session"
            / "ui"
            / "src"
            / "runefoble-initiative-tracker.styles.ts",
            "style_export": "initiativeTrackerStyles",
            "tag": "runefoble-initiative-tracker",
            "max_style_lines": 150,
            "max_comp_lines": 250,
            "events": ["turn-timer-expired", "initiative-turn-advanced"],
        },
        {
            "component": REPO_ROOT
            / "services"
            / "character_sheet"
            / "ui"
            / "src"
            / "runefoble-absentee-recap.ts",
            "styles": REPO_ROOT
            / "services"
            / "character_sheet"
            / "ui"
            / "src"
            / "runefoble-absentee-recap.styles.ts",
            "style_export": "absenteeRecapStyles",
            "tag": "runefoble-absentee-recap",
            "max_style_lines": 140,
            "max_comp_lines": 240,
            "events": ["audio-toggle"],
        },
        {
            "component": REPO_ROOT
            / "services"
            / "game_session"
            / "ui"
            / "src"
            / "runefoble-spectator-view.ts",
            "styles": REPO_ROOT
            / "services"
            / "game_session"
            / "ui"
            / "src"
            / "runefoble-spectator-view.styles.ts",
            "style_export": "spectatorViewStyles",
            "tag": "runefoble-spectator-view",
            "max_style_lines": 130,
            "max_comp_lines": 250,
            "events": [],
        },
    ]

    for item in decomposed_targets:
        comp_file = item["component"]
        styles_file = item["styles"]

        assert comp_file.is_file(), f"{comp_file} must exist"
        assert styles_file.is_file(), f"{styles_file} must exist"

        comp_content = comp_file.read_text(encoding="utf-8")
        styles_content = styles_file.read_text(encoding="utf-8")

        comp_lines = len(comp_content.splitlines())
        style_lines = len(styles_content.splitlines())

        # Enforce strict line count ceilings (Hard Invariant 6 & TASK-0043 spec)
        assert comp_lines < item["max_comp_lines"], (
            f"{comp_file.name} has {comp_lines} lines (expected < {item['max_comp_lines']})"
        )
        assert style_lines < item["max_style_lines"], (
            f"{styles_file.name} has {style_lines} lines (expected < {item['max_style_lines']})"
        )
        assert comp_lines < 250, f"{comp_file.name} must be < 250 lines"
        assert style_lines < 250, f"{styles_file.name} must be < 250 lines"

        # Style module exports the css template
        assert f"export const {item['style_export']} = css`" in styles_content
        # Component module imports and uses the style export
        assert item["style_export"] in comp_content
        assert f"@customElement('{item['tag']}')" in comp_content

        # Contract preservation: custom events
        for event_name in item["events"]:
            assert f"'{event_name}'" in comp_content, (
                f"Event {event_name} missing in {comp_file.name}"
            )


def test_task_0061_tactical_board_dm_and_voice_styles_decomposition():
    """Verify TASK-0061: CSS styles extracted to companion *.styles.ts modules and Hard Invariant 6."""
    targets = [
        {
            "component": REPO_ROOT / "services/board_state/ui/src/runefoble-board.ts",
            "styles": REPO_ROOT / "services/board_state/ui/src/runefoble-board.styles.ts",
            "style_export": "boardStyles",
            "tag": "runefoble-board",
            "max_style_lines": 220,
            "max_comp_lines": 250,
            "events": ["move-token", "confirm-ghost", "cancel-ghost", "ghost-timeout"],
        },
        {
            "component": REPO_ROOT / "services/the_watcher/ui/src/runefoble-autonomous-dm.ts",
            "styles": REPO_ROOT / "services/the_watcher/ui/src/runefoble-autonomous-dm.styles.ts",
            "style_export": "autonomousDmStyles",
            "tag": "runefoble-autonomous-dm",
            "max_style_lines": 230,
            "max_comp_lines": 200,
            "events": ["generate-scene", "spawn-encounter"],
        },
        {
            "component": REPO_ROOT / "services/voice_agent/ui/src/runefoble-voice-controls.ts",
            "styles": REPO_ROOT / "services/voice_agent/ui/src/runefoble-voice-controls.styles.ts",
            "style_export": "voiceControlsStyles",
            "tag": "runefoble-voice-controls",
            "max_style_lines": 160,
            "max_comp_lines": 240,
            "events": ["voice-toggle", "voice-state", "voice-level"],
        },
    ]

    for item in targets:
        comp_file = item["component"]
        styles_file = item["styles"]

        assert comp_file.is_file(), f"{comp_file} must exist"
        assert styles_file.is_file(), f"{styles_file} must exist"

        comp_content = comp_file.read_text(encoding="utf-8")
        styles_content = styles_file.read_text(encoding="utf-8")

        comp_lines = len(comp_content.splitlines())
        style_lines = len(styles_content.splitlines())

        assert comp_lines < item["max_comp_lines"], (
            f"{comp_file.name} has {comp_lines} lines (expected < {item['max_comp_lines']})"
        )
        assert style_lines < item["max_style_lines"], (
            f"{styles_file.name} has {style_lines} lines (expected < {item['max_style_lines']})"
        )
        assert comp_lines < 250, f"{comp_file.name} must be < 250 lines"
        assert style_lines < 250, f"{styles_file.name} must be < 250 lines"

        assert item["style_export"] in styles_content
        assert item["style_export"] in comp_content
        assert f"@customElement('{item['tag']}')" in comp_content

        for event_name in item["events"]:
            assert f"'{event_name}'" in comp_content, (
                f"Event {event_name} missing in {comp_file.name}"
            )
