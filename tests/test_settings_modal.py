"""Blackbox tests for Settings Modal Coordinator and Dialog Shell (TASK-0073, TASK-0086).

Governing ADRs: ADR-0004, ADR-0012, ADR-0013.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
APP_TS = FRONTEND_DIR / "src" / "runefoble-app.ts"
SETTINGS_MODAL_TS = FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.ts"
SETTINGS_MODAL_STYLES_TS = (
    FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.styles.ts"
)
SETTINGS_LAYOUT_STYLES_TS = (
    FRONTEND_DIR / "src" / "components" / "styles" / "settings-modal-layout.styles.ts"
)
HEADER_TS = FRONTEND_DIR / "src" / "components" / "runefoble-header.ts"
STORIES_TS = FRONTEND_DIR / "src" / "stories" / "runefoble-settings-modal.stories.ts"
INDEX_TS = FRONTEND_DIR / "src" / "index.ts"
THEMES_CSS = FRONTEND_DIR / "src" / "styles" / "themes.css"


def test_settings_modal_registration_and_properties():
    """Verify runefoble-settings-modal coordinator registration and reactive properties."""
    assert SETTINGS_MODAL_TS.is_file(), "runefoble-settings-modal.ts must exist"
    content = SETTINGS_MODAL_TS.read_text(encoding="utf-8")
    assert "@customElement('runefoble-settings-modal')" in content
    assert "class RunefobleSettingsModal extends LitElement" in content
    assert "@property({ type: Boolean, reflect: true }) open: boolean = false;" in content
    assert "currentTheme: ThemeMode = 'bauhaus';" in content
    assert "currentColorMode: ColorMode = 'system';" in content
    assert "'runefoble-settings-modal': RunefobleSettingsModal;" in content


def test_settings_modal_dialog_architecture():
    """Verify modal dialog backdrop overlay, accessibility ARIA attributes, and focus trap."""
    content = SETTINGS_MODAL_TS.read_text(encoding="utf-8")
    styles_content = (
        SETTINGS_LAYOUT_STYLES_TS.read_text(encoding="utf-8")
        if SETTINGS_LAYOUT_STYLES_TS.is_file()
        else SETTINGS_MODAL_STYLES_TS.read_text(encoding="utf-8")
    )
    assert ".modal-overlay" in styles_content
    assert "backdrop-filter: blur(4px)" in styles_content
    assert 'role="dialog"' in content
    assert 'aria-modal="true"' in content
    assert 'aria-labelledby="settings-modal-title"' in content
    assert 'aria-label="Close settings"' in content
    assert "@click=${this.closeModal}" in content
    assert "handleBackdropClick" in content
    assert "handleKeyDown" in content
    assert "Escape" in content
    assert "handleFocusTrap" in content
    assert "triggerElement" in content
    assert "settings-closed" in content


def test_extensible_settings_sections():
    """Verify tabs navigation and delegated subcomponents in modal coordinator."""
    content = SETTINGS_MODAL_TS.read_text(encoding="utf-8")
    assert "Appearance & Theme" in content
    assert "Audio & Voice Input" in content
    assert "Dice & Physics" in content
    assert "runefoble-settings-appearance" in content
    assert "runefoble-settings-audio" in content
    assert "runefoble-settings-dice" in content


def test_app_header_integration():
    """Verify inline switcher is replaced with Settings trigger button and modal is integrated."""
    app_content = APP_TS.read_text(encoding="utf-8")
    header_content = HEADER_TS.read_text(encoding="utf-8")
    assert "<runefoble-theme-switcher></runefoble-theme-switcher>" not in app_content
    assert "<runefoble-theme-switcher></runefoble-theme-switcher>" not in header_content
    assert 'id="settings-trigger-btn"' in header_content
    assert 'class="settings-trigger"' in header_content
    assert 'aria-haspopup="dialog"' in header_content
    assert 'aria-label="Open settings"' in header_content
    assert "<runefoble-header" in app_content
    assert "<runefoble-settings-modal" in app_content
    assert "@settings-closed=${this.handleSettingsClosed}" in app_content


def test_index_export():
    """Verify runefoble-settings-modal and subcomponents are exported from index.ts."""
    index_content = INDEX_TS.read_text(encoding="utf-8")
    assert "export * from './components/runefoble-settings-modal.ts';" in index_content
    modal_content = SETTINGS_MODAL_TS.read_text(encoding="utf-8")
    assert "export * from './settings/runefoble-settings-appearance.ts';" in modal_content
    assert "export * from './settings/runefoble-settings-audio.ts';" in modal_content
    assert "export * from './settings/runefoble-settings-dice.ts';" in modal_content


def test_storybook_stories_completeness():
    """Verify Storybook stories exist covering default trigger, light, dark, and themes."""
    assert STORIES_TS.is_file(), "runefoble-settings-modal.stories.ts must exist"
    stories_content = STORIES_TS.read_text(encoding="utf-8")
    assert "Settings/RunefobleSettingsModal" in stories_content
    assert "DefaultClosedTrigger" in stories_content
    assert "OpenLightMode" in stories_content
    assert "OpenDarkMode" in stories_content
    assert "ActiveThemeCyberRune" in stories_content


def test_dark_mode_css_tokens():
    """Verify themes.css defines dark mode overrides and system media query rules."""
    css_content = THEMES_CSS.read_text(encoding="utf-8")
    assert '[data-theme="bauhaus"][data-color-mode="dark"]' in css_content
    assert "--rf-bg-canvas: #121212;" in css_content
    assert "@media (prefers-color-scheme: dark)" in css_content
