"""Blackbox tests for Settings Modal Modular Subcomponents (TASK-0086).

Governing ADRs: ADR-0004, ADR-0012, ADR-0013.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_DIR = REPO_ROOT / "frontend" / "src" / "components" / "settings"
MODAL_TS = REPO_ROOT / "frontend" / "src" / "components" / "runefoble-settings-modal.ts"
APPEARANCE_TS = SETTINGS_DIR / "runefoble-settings-appearance.ts"
AUDIO_TS = SETTINGS_DIR / "runefoble-settings-audio.ts"
DICE_TS = SETTINGS_DIR / "runefoble-settings-dice.ts"
CONTROLLER_TS = SETTINGS_DIR / "settings-theme-controller.ts"


def test_appearance_subcomponent_and_controller():
    """Verify Appearance tab panel and ThemeSettingsController reactive logic."""
    assert APPEARANCE_TS.is_file() and CONTROLLER_TS.is_file()
    app_code = APPEARANCE_TS.read_text(encoding="utf-8")
    ctrl_code = CONTROLLER_TS.read_text(encoding="utf-8")
    assert "@customElement('runefoble-settings-appearance')" in app_code
    assert 'aria-label="Appearance color mode"' in app_code
    assert "setColorMode('light')" in app_code
    assert "setColorMode('dark')" in app_code
    assert "setColorMode('system')" in app_code
    assert "swatch-chip" in app_code
    assert "class ThemeSettingsController" in ctrl_code
    assert "window.localStorage.getItem('runefoble-color-mode')" in ctrl_code
    assert "window.localStorage.setItem('runefoble-color-mode', mode)" in ctrl_code
    assert "document.documentElement.setAttribute('data-color-mode', mode)" in ctrl_code
    assert "window.localStorage.setItem('runefoble-theme', theme)" in ctrl_code
    assert "document.documentElement.setAttribute('data-theme', theme)" in ctrl_code
    assert "matchMedia('(prefers-color-scheme: dark)')" in ctrl_code
    assert "color-mode-changed" in ctrl_code
    assert "theme-changed" in ctrl_code


def test_audio_subcomponent():
    """Verify Audio tab panel device selector, noise suppression, and permission indicator."""
    assert AUDIO_TS.is_file()
    code = AUDIO_TS.read_text(encoding="utf-8")
    assert "@customElement('runefoble-settings-audio')" in code
    assert "audio-input-device" in code
    assert "noiseSuppression" in code
    assert "Microphone Permission: Ready" in code


def test_dice_subcomponent():
    """Verify Dice tab panel physics, spatial audio, and d20 test roll."""
    assert DICE_TS.is_file()
    code = DICE_TS.read_text(encoding="utf-8")
    assert "@customElement('runefoble-settings-dice')" in code
    assert "dicePhysics" in code
    assert "diceSound" in code
    assert "test-roll-btn" in code
    assert "dice-test-roll" in code


def test_all_settings_files_under_150_lines():
    """Verify all settings components, controllers, and tests comply with <150 lines limit."""
    files = [MODAL_TS, APPEARANCE_TS, AUDIO_TS, DICE_TS, CONTROLLER_TS, Path(__file__)]
    for f in files:
        assert f.is_file(), f"{f} must exist"
        line_count = len(f.read_text(encoding="utf-8").splitlines())
        assert line_count < 150, f"{f.name} exceeds 150 lines: {line_count} lines"
