"""Blackbox tests for App Shell Orchestration and Storybook Aggregation.

Verifies that frontend/src/runefoble-app.ts orchestrates service microfrontends,
pnpm-workspace.yaml links packages, Storybook discovers all service stories,
and component style extractions adhere to Hard Invariant 6 (< 500 lines limit).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_app_shell_microfrontend_composition():
    """Verify frontend/src/runefoble-app.ts acts as the App Shell orchestrating microfrontends."""
    shell_file = REPO_ROOT / "frontend/src/runefoble-app.ts"
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
    sb_main = REPO_ROOT / "frontend/.storybook/main.ts"
    assert sb_main.is_file()
    content = sb_main.read_text(encoding="utf-8")
    assert "services/*/ui/src/**/*.stories" in content


def test_voice_controls_visualizer_and_webrtc_spec():
    """Verify runefoble-voice-controls implements WebAudio AnalyserNode visualizer & WebRTC monitor."""
    ui_src = REPO_ROOT / "services/voice_agent/ui/src"
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
    stories_file = REPO_ROOT / "services/voice_agent/ui/src/runefoble-voice-controls.stories.ts"
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")

    assert "DefaultMuted" in content
    assert "Inactive" in content
    assert "WaveformActive" in content
    assert "LowBandwidthWarning" in content
    assert "AfflictionDspActive" in content


def _assert_decomposed_targets(targets: list[dict]) -> None:
    """Helper to verify companion *.styles.ts extraction and line count invariant."""
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

        assert (
            f"export const {item['style_export']} = css`" in styles_content
            or item["style_export"] in styles_content
        )
        assert item["style_export"] in comp_content
        assert f"@customElement('{item['tag']}')" in comp_content

        for event_name in item["events"]:
            assert f"'{event_name}'" in comp_content, (
                f"Event {event_name} missing in {comp_file.name}"
            )


def test_microfrontend_component_styles_and_subview_decomposition_integrity():
    """Verify TASK-0043: CSS styles extracted to *.styles.ts companion modules and file length limits."""
    decomposed_targets = [
        {
            "component": REPO_ROOT / "services/game_session/ui/src/runefoble-initiative-tracker.ts",
            "styles": REPO_ROOT
            / "services/game_session/ui/src/runefoble-initiative-tracker.styles.ts",
            "style_export": "initiativeTrackerStyles",
            "tag": "runefoble-initiative-tracker",
            "max_style_lines": 150,
            "max_comp_lines": 250,
            "events": ["turn-timer-expired", "initiative-turn-advanced"],
        },
        {
            "component": REPO_ROOT / "services/character_sheet/ui/src/runefoble-absentee-recap.ts",
            "styles": REPO_ROOT
            / "services/character_sheet/ui/src/runefoble-absentee-recap.styles.ts",
            "style_export": "absenteeRecapStyles",
            "tag": "runefoble-absentee-recap",
            "max_style_lines": 140,
            "max_comp_lines": 240,
            "events": ["audio-toggle"],
        },
        {
            "component": REPO_ROOT / "services/game_session/ui/src/runefoble-spectator-view.ts",
            "styles": REPO_ROOT / "services/game_session/ui/src/runefoble-spectator-view.styles.ts",
            "style_export": "spectatorViewStyles",
            "tag": "runefoble-spectator-view",
            "max_style_lines": 130,
            "max_comp_lines": 250,
            "events": [],
        },
    ]
    _assert_decomposed_targets(decomposed_targets)


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
    _assert_decomposed_targets(targets)
