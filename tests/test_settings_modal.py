"""Blackbox tests for Settings Modal, Color Mode, and Integrated Theme Switcher (TASK-0073).

Governing ADRs: ADR-0004, ADR-0012
User Stories: US-0041, US-0042
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
APP_TS = FRONTEND_DIR / "src" / "runefoble-app.ts"
SETTINGS_MODAL_TS = FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.ts"
SETTINGS_MODAL_STYLES_TS = (
    FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.styles.ts"
)
SETTINGS_MODAL_TYPES_TS = FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.types.ts"
HEADER_TS = FRONTEND_DIR / "src" / "components" / "runefoble-header.ts"
STORIES_TS = FRONTEND_DIR / "src" / "stories" / "runefoble-settings-modal.stories.ts"
INDEX_TS = FRONTEND_DIR / "src" / "index.ts"
THEMES_CSS = FRONTEND_DIR / "src" / "styles" / "themes.css"


def test_settings_modal_registration_and_properties():
    """Verify runefoble-settings-modal component registration and reactive properties."""
    assert SETTINGS_MODAL_TS.is_file(), "runefoble-settings-modal.ts must exist"
    content = SETTINGS_MODAL_TS.read_text(encoding="utf-8")

    assert "@customElement('runefoble-settings-modal')" in content
    assert "class RunefobleSettingsModal extends LitElement" in content

    # Properties
    assert "@property({ type: Boolean, reflect: true }) open: boolean = false;" in content
    assert "currentTheme: ThemeMode = 'bauhaus';" in content
    assert "currentColorMode: ColorMode = 'system';" in content

    # Global registration
    assert "'runefoble-settings-modal': RunefobleSettingsModal;" in content


def test_settings_modal_dialog_architecture():
    """Verify modal dialog backdrop overlay, accessibility ARIA attributes, and dismiss mechanisms."""
    content = SETTINGS_MODAL_TS.read_text(encoding="utf-8")
    styles_content = SETTINGS_MODAL_STYLES_TS.read_text(encoding="utf-8")

    # Backdrop overlay and blur
    assert ".modal-overlay" in styles_content
    assert "backdrop-filter: blur(4px)" in styles_content
    assert "background: rgba(0, 0, 0, 0.65)" in styles_content

    # Dialog accessibility semantics
    assert 'role="dialog"' in content
    assert 'aria-modal="true"' in content
    assert 'aria-labelledby="settings-modal-title"' in content

    # Close button & backdrop click
    assert 'aria-label="Close settings"' in content
    assert "@click=${this.closeModal}" in content
    assert "handleBackdropClick" in content
    assert "handleKeyDown" in content
    assert "Escape" in content

    # Focus trap and trigger restoration
    assert "handleFocusTrap" in content
    assert "triggerElement" in content
    assert "settings-closed" in content


def test_color_mode_controls_and_media_query():
    """Verify Dark, Light, and System segmented controls, local storage sync, and media query listener."""
    content = SETTINGS_MODAL_TS.read_text(encoding="utf-8")

    # Segmented toggle buttons
    assert 'aria-label="Appearance color mode"' in content
    assert "@click=${() => this.setColorMode('light')}" in content
    assert "@click=${() => this.setColorMode('dark')}" in content
    assert "@click=${() => this.setColorMode('system')}" in content

    # LocalStorage persistence
    assert "runefoble-color-mode" in content
    assert "window.localStorage.getItem('runefoble-color-mode')" in content
    assert "window.localStorage.setItem('runefoble-color-mode', mode)" in content

    # Document element attribute
    assert "document.documentElement.setAttribute('data-color-mode', mode)" in content

    # System prefers-color-scheme media query
    assert "matchMedia('(prefers-color-scheme: dark)')" in content
    assert "dispatchColorModeEvent" in content
    assert "color-mode-changed" in content


def test_theme_selection_cards():
    """Verify visual theme selection cards for all four themes with palette swatches and event dispatch."""
    content = SETTINGS_MODAL_TS.read_text(encoding="utf-8")
    types_content = SETTINGS_MODAL_TYPES_TS.read_text(encoding="utf-8")

    # Four themes supported
    assert "'bauhaus'" in types_content
    assert "'dark-fantasy'" in types_content
    assert "'parchment'" in types_content
    assert "'cyber-rune'" in types_content

    # Swatch chips and badges
    assert "swatches" in types_content
    assert "swatch-chip" in content
    assert "@click=${() => this.setTheme(opt.id)}" in content

    # Document element and persistence
    assert "document.documentElement.setAttribute('data-theme', theme)" in content
    assert "window.localStorage.setItem('runefoble-theme', theme)" in content
    assert "theme-changed" in content


def test_extensible_settings_sections():
    """Verify tabs for Appearance & Theme, Audio & Voice Input, and Dice & Physics."""
    content = SETTINGS_MODAL_TS.read_text(encoding="utf-8")

    # Tabs navigation
    assert "Appearance & Theme" in content
    assert "Audio & Voice Input" in content
    assert "Dice & Physics" in content

    # Audio form controls
    assert "audio-input-device" in content
    assert "noiseSuppression" in content

    # Dice controls
    assert "dicePhysics" in content
    assert "diceSound" in content


def test_app_header_integration():
    """Verify inline switcher is replaced with Settings trigger button in header and modal is integrated."""
    app_content = APP_TS.read_text(encoding="utf-8")
    header_content = HEADER_TS.read_text(encoding="utf-8")

    # Inline switcher removed from header actions
    assert "<runefoble-theme-switcher></runefoble-theme-switcher>" not in app_content
    assert "<runefoble-theme-switcher></runefoble-theme-switcher>" not in header_content

    # Settings trigger button present with ARIA attributes in runefoble-header
    assert 'id="settings-trigger-btn"' in header_content
    assert 'class="settings-trigger"' in header_content
    assert 'aria-haspopup="dialog"' in header_content
    assert 'aria-label="Open settings"' in header_content
    assert "aria-expanded" in header_content
    assert "Settings" in header_content
    assert "⚙️" in header_content

    # Header and settings modal integrated into app shell
    assert "<runefoble-header" in app_content
    assert "<runefoble-settings-modal" in app_content
    assert "@settings-closed=${this.handleSettingsClosed}" in app_content
    assert "initThemeAndColorMode()" in app_content


def test_index_export():
    """Verify runefoble-settings-modal is exported from index.ts."""
    index_content = INDEX_TS.read_text(encoding="utf-8")
    assert "export * from './components/runefoble-settings-modal.ts';" in index_content


def test_storybook_stories_completeness():
    """Verify Storybook stories exist covering default trigger, light, dark, system, and theme selections."""
    assert STORIES_TS.is_file(), "runefoble-settings-modal.stories.ts must exist"
    stories_content = STORIES_TS.read_text(encoding="utf-8")

    assert "Settings/RunefobleSettingsModal" in stories_content
    assert "DefaultClosedTrigger" in stories_content
    assert "OpenLightMode" in stories_content
    assert "OpenDarkMode" in stories_content
    assert "OpenSystemMode" in stories_content
    assert "ActiveThemeCyberRune" in stories_content
    assert "ActiveThemeDarkFantasy" in stories_content
    assert "ActiveThemeParchment" in stories_content


def test_dark_mode_css_tokens():
    """Verify themes.css defines dark mode overrides and system media query rules."""
    css_content = THEMES_CSS.read_text(encoding="utf-8")

    # Bauhaus in dark mode
    assert '[data-theme="bauhaus"][data-color-mode="dark"]' in css_content
    assert "--rf-bg-canvas: #121212;" in css_content
    assert "--rf-shadow-color:" in css_content
    assert "--rf-shadow: 4px 4px 0px var(--rf-shadow-color);" in css_content

    # System media query
    assert "@media (prefers-color-scheme: dark)" in css_content


def test_all_touched_files_under_500_lines():
    """Verify all files touched by TASK-0073 comply strictly with <500 lines limit."""
    files = [
        APP_TS,
        HEADER_TS,
        SETTINGS_MODAL_TS,
        SETTINGS_MODAL_STYLES_TS,
        SETTINGS_MODAL_TYPES_TS,
        STORIES_TS,
        THEMES_CSS,
        INDEX_TS,
        Path(__file__),
    ]
    for file_path in files:
        assert file_path.is_file(), f"{file_path} must exist"
        lines = file_path.read_text(encoding="utf-8").splitlines()
        line_count = len(lines)
        assert line_count < 500, f"{file_path.name} exceeds 500 lines: {line_count} lines"
