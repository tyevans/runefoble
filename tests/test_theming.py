"""Tests for Frontend Theming System, Color Tokens, and Contrast Invariants (TASK-0012, TASK-0074)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
THEMES_CSS = FRONTEND_DIR / "src" / "styles" / "themes.css"
THEMES_BASE_CSS = FRONTEND_DIR / "src" / "styles" / "themes" / "base.css"
THEMES_BAUHAUS_CSS = FRONTEND_DIR / "src" / "styles" / "themes" / "bauhaus.css"
THEMES_DARK_FANTASY_CSS = FRONTEND_DIR / "src" / "styles" / "themes" / "dark-fantasy.css"
THEMES_PARCHMENT_CSS = FRONTEND_DIR / "src" / "styles" / "themes" / "parchment.css"
THEMES_CYBER_RUNE_CSS = FRONTEND_DIR / "src" / "styles" / "themes" / "cyber-rune.css"
THEME_SUBMODULES = [
    THEMES_BASE_CSS,
    THEMES_BAUHAUS_CSS,
    THEMES_DARK_FANTASY_CSS,
    THEMES_PARCHMENT_CSS,
    THEMES_CYBER_RUNE_CSS,
]
INDEX_CSS = FRONTEND_DIR / "src" / "index.css"
INDEX_HTML = FRONTEND_DIR / "index.html"
INDEX_TS = FRONTEND_DIR / "src" / "index.ts"

APP_TS = FRONTEND_DIR / "src" / "runefoble-app.ts"
HEADER_TS = FRONTEND_DIR / "src" / "components" / "runefoble-header.ts"
CAMPAIGN_NAV_TS = FRONTEND_DIR / "src" / "components" / "runefoble-campaign-nav.ts"
APP_SHELL_STYLES_TS = FRONTEND_DIR / "src" / "styles" / "app-shell.styles.ts"
SWITCHER_TS = FRONTEND_DIR / "src" / "components" / "runefoble-theme-switcher.ts"
BOARD_TS = REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-board.ts"
CARD_TS = REPO_ROOT / "services" / "character_sheet" / "ui" / "src" / "runefoble-character-card.ts"
FEED_TS = REPO_ROOT / "services" / "the_watcher" / "ui" / "src" / "runefoble-watcher-feed.ts"
AUTONOMOUS_DM_STYLES_TS = (
    REPO_ROOT / "services" / "the_watcher" / "ui" / "src" / "runefoble-autonomous-dm.styles.ts"
)
VOICE_TS = REPO_ROOT / "services" / "voice_agent" / "ui" / "src" / "runefoble-voice-controls.ts"
VOICE_STYLES_TS = (
    REPO_ROOT / "services" / "voice_agent" / "ui" / "src" / "runefoble-voice-controls.styles.ts"
)
STORIES_TS = FRONTEND_DIR / "src" / "stories" / "theme-switcher.stories.ts"
PREVIEW_TS = FRONTEND_DIR / ".storybook" / "preview.ts"
CONTRAST_STORIES_TS = FRONTEND_DIR / "src" / "stories" / "theme-contrast-matrix.stories.ts"

SETTINGS_MODAL_LAYOUT_STYLES_TS = (
    FRONTEND_DIR / "src" / "components" / "styles" / "settings-modal-layout.styles.ts"
)
SETTINGS_MODAL_TABS_STYLES_TS = (
    FRONTEND_DIR / "src" / "components" / "styles" / "settings-modal-tabs.styles.ts"
)
SETTINGS_MODAL_CONTROLS_STYLES_TS = (
    FRONTEND_DIR / "src" / "components" / "styles" / "settings-modal-controls.styles.ts"
)

COMPONENT_FILES = [
    APP_SHELL_STYLES_TS,
    HEADER_TS,
    CAMPAIGN_NAV_TS,
    SWITCHER_TS,
    SETTINGS_MODAL_LAYOUT_STYLES_TS,
    SETTINGS_MODAL_TABS_STYLES_TS,
    SETTINGS_MODAL_CONTROLS_STYLES_TS,
    REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-board.styles.ts",
    REPO_ROOT / "services" / "board_state" / "ui" / "src" / "ghost_preview.styles.ts",
    REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-map-uploader.styles.ts",
    CARD_TS,
    REPO_ROOT
    / "services"
    / "character_sheet"
    / "ui"
    / "src"
    / "runefoble-absentee-recap.styles.ts",
    REPO_ROOT / "services" / "game_session" / "ui" / "src" / "runefoble-dice-roller.ts",
    REPO_ROOT
    / "services"
    / "game_session"
    / "ui"
    / "src"
    / "runefoble-initiative-tracker.styles.ts",
    REPO_ROOT / "services" / "game_session" / "ui" / "src" / "runefoble-spectator-view.styles.ts",
    FEED_TS,
    AUTONOMOUS_DM_STYLES_TS,
    VOICE_STYLES_TS,
    REPO_ROOT / "services" / "voice_agent" / "ui" / "src" / "runefoble-audio-indicator.ts",
]

SEMANTIC_SURFACE_TOKENS = [
    "--rf-bg-canvas",
    "--rf-bg-surface",
    "--rf-bg-surface-elevated",
    "--rf-bg-card",
    "--rf-bg-inset",
]

SEMANTIC_TEXT_TOKENS = [
    "--rf-text-primary",
    "--rf-text-secondary",
    "--rf-text-muted",
    "--rf-text-inverse",
]

SEMANTIC_BORDER_TOKENS = [
    "--rf-border-color",
    "--rf-border-subtle",
    "--rf-border-focus",
]

SEMANTIC_SHADOW_TOKENS = [
    "--rf-shadow-color",
    "--rf-shadow",
    "--rf-shadow-sm",
]


def resolve_css_imports(file_path: Path) -> str:
    """Recursively resolve CSS @import statements from the given stylesheet."""
    content = file_path.read_text(encoding="utf-8")
    base_dir = file_path.parent

    def replace_import(match: re.Match) -> str:
        rel_path = match.group(1)
        imported_file = (base_dir / rel_path).resolve()
        if imported_file.is_file():
            return resolve_css_imports(imported_file)
        return match.group(0)

    return re.sub(r"""@import\s+['"]([^'"]+)['"]\s*;""", replace_import, content)


def test_themes_css_semantic_token_hierarchy():
    """Verify themes.css defines the full semantic token hierarchy across all themes and color modes."""
    assert THEMES_CSS.is_file(), "themes.css must exist"
    content = resolve_css_imports(THEMES_CSS)

    # Verify root / base selectors exist
    assert ":root" in content
    assert '[data-color-mode="light"]' in content
    assert '[data-color-mode="dark"]' in content
    assert "@media (prefers-color-scheme: dark)" in content

    # Verify all 4 core themes have explicit light and dark variations
    themes = ["bauhaus", "dark-fantasy", "parchment", "cyber-rune"]
    for theme in themes:
        assert f'[data-theme="{theme}"]' in content
        assert (
            f'[data-theme="{theme}"][data-color-mode="light"]' in content
            or f'[data-theme="{theme}"]' in content
        )
        assert f'[data-theme="{theme}"][data-color-mode="dark"]' in content

    # Verify presence of all required semantic tokens in themes.css
    all_tokens = (
        SEMANTIC_SURFACE_TOKENS
        + SEMANTIC_TEXT_TOKENS
        + SEMANTIC_BORDER_TOKENS
        + SEMANTIC_SHADOW_TOKENS
    )
    for token in all_tokens:
        assert token in content, f"Missing required semantic token {token} in themes.css"

    # Verify tactile neobrutalist border/shadow defaults
    assert "--rf-border-width" in content
    assert "--rf-shadow:" in content
    assert "--rf-shadow-sm:" in content


def test_wcag_contrast_ratios_across_theme_matrix():
    """Verify WCAG 2.1 AA (min 4.5:1 for body) and AAA (min 7:1 for primary) contrast invariants."""
    content = resolve_css_imports(THEMES_CSS)
    blocks = re.findall(r"([^{]+)\{([^}]+)\}", content)

    def srgb_to_lin(color_channel: int) -> float:
        c = color_channel / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    def luminance(hex_code: str) -> float:
        h = hex_code.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)

    def contrast(c1: str, c2: str) -> float:
        l1, l2 = luminance(c1), luminance(c2)
        lighter, darker = max(l1, l2), min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    checked_blocks = 0
    for selector, body in blocks:
        if "data-theme" in selector:
            vars_dict = dict(re.findall(r"(--rf-[a-z0-9\-]+):\s*([^;]+);", body))
            tp = vars_dict.get("--rf-text-primary", "").strip()
            ts = vars_dict.get("--rf-text-secondary", "").strip()
            bg_c = vars_dict.get("--rf-bg-canvas", "").strip()
            bg_s = vars_dict.get("--rf-bg-surface", "").strip()

            if tp.startswith("#") and bg_c.startswith("#"):
                ratio_primary = contrast(tp, bg_c)
                assert ratio_primary >= 7.0, (
                    f"Primary text contrast failure in {selector.strip()}: {ratio_primary:.2f} < 7.0"
                )
                checked_blocks += 1

            if ts.startswith("#") and bg_c.startswith("#"):
                ratio_secondary = contrast(ts, bg_c)
                assert ratio_secondary >= 4.5, (
                    f"Secondary text contrast failure in {selector.strip()}: {ratio_secondary:.2f} < 4.5"
                )

            if tp.startswith("#") and bg_s.startswith("#"):
                ratio_surface = contrast(tp, bg_s)
                assert ratio_surface >= 7.0, (
                    f"Surface primary text contrast failure in {selector.strip()}: {ratio_surface:.2f} < 7.0"
                )

    assert checked_blocks >= 8, f"Expected at least 8 theme/mode variations, found {checked_blocks}"


def test_zero_hardcoded_hexes_in_web_components_static_styles():
    """Verify zero hardcoded hex color literals in Web Component static styles blocks."""
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")
    css_block_pattern = re.compile(r"(?:static\s+styles\s*=\s*css|css)`([\s\S]*?)`")

    for file_path in COMPONENT_FILES:
        assert file_path.is_file(), f"{file_path} must exist"
        content = file_path.read_text(encoding="utf-8")
        matches = css_block_pattern.findall(content)
        assert len(matches) > 0, f"Expected CSS style block in {file_path.name}"

        for block in matches:
            hex_occurrences = hex_pattern.findall(block)
            assert len(hex_occurrences) == 0, (
                f"Found hardcoded hex literals {hex_occurrences} in {file_path.name} CSS styles"
            )


def test_frontend_index_css_and_html():
    """Verify index.css imports themes.css and uses theme tokens."""
    index_css = INDEX_CSS.read_text(encoding="utf-8")
    assert "@import './styles/themes.css';" in index_css
    assert "var(--rf-bg-canvas)" in index_css
    assert "var(--rf-text-primary)" in index_css

    index_html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'rel="stylesheet" href="./src/index.css"' in index_html
    assert "<runefoble-app></runefoble-app>" in index_html


def test_theme_switcher_component():
    """Verify <runefoble-theme-switcher> Lit component."""
    assert SWITCHER_TS.is_file(), "runefoble-theme-switcher.ts must exist"
    content = SWITCHER_TS.read_text(encoding="utf-8")

    # LocalStorage handling
    assert "runefoble-theme" in content
    assert "localStorage" in content

    # Root attribute manipulation
    assert "document.documentElement.setAttribute('data-theme', theme)" in content

    # Event dispatch
    assert "theme-changed" in content

    # Supported theme modes
    assert "'bauhaus'" in content
    assert "'dark-fantasy'" in content
    assert "'parchment'" in content
    assert "'cyber-rune'" in content

    # Index export
    index_ts = INDEX_TS.read_text(encoding="utf-8")
    assert "export * from './components/runefoble-theme-switcher.ts';" in index_ts


def test_components_adopt_tokens():
    """Verify components consume --rf-* tokens."""
    app_content = APP_TS.read_text(encoding="utf-8")
    header_content = HEADER_TS.read_text(encoding="utf-8")
    styles_content = APP_SHELL_STYLES_TS.read_text(encoding="utf-8")
    assert "import './styles/themes.css';" in app_content
    assert "<runefoble-settings-modal" in app_content
    assert "settings-trigger" in header_content
    assert "var(--rf-bg-canvas" in styles_content
    assert "var(--rf-text-primary" in styles_content
    assert "var(--rf-border-color" in header_content

    board_styles = (
        REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-board.styles.ts"
    ).read_text(encoding="utf-8")
    assert "var(--rf-" in board_styles
    assert "var(--rf-border-color" in board_styles

    card_content = CARD_TS.read_text(encoding="utf-8")
    assert "var(--rf-" in card_content
    assert "var(--rf-bg-card" in card_content

    feed_content = FEED_TS.read_text(encoding="utf-8")
    assert "var(--rf-" in feed_content
    assert "var(--rf-shadow" in feed_content

    voice_content = VOICE_STYLES_TS.read_text(encoding="utf-8")
    assert "var(--rf-" in voice_content
    assert "var(--rf-border-color" in voice_content


def test_storybook_stories_exist():
    """Verify Storybook stories exist and contain theme variations."""
    assert STORIES_TS.is_file(), "theme-switcher.stories.ts must exist"
    content = STORIES_TS.read_text(encoding="utf-8")
    assert "Theme/RunefobleThemeSwitcher" in content
    assert "BauhausModernist" in content
    assert "DarkFantasy" in content
    assert "Parchment" in content
    assert "CyberRune" in content


def test_storybook_color_mode_and_theme_matrix():
    """Verify Storybook toolbar preview configuration and side-by-side theme contrast stories."""
    assert PREVIEW_TS.is_file(), "Storybook preview.ts must exist"
    preview_content = PREVIEW_TS.read_text(encoding="utf-8")

    # Global toolbar types for both theme and colorMode
    assert "colorMode:" in preview_content
    assert "theme:" in preview_content
    assert "'light'" in preview_content
    assert "'dark'" in preview_content
    assert "'system'" in preview_content
    assert "data-color-mode" in preview_content
    assert "data-theme" in preview_content

    # Contrast matrix story file
    assert CONTRAST_STORIES_TS.is_file(), "theme-contrast-matrix.stories.ts must exist"
    stories_content = CONTRAST_STORIES_TS.read_text(encoding="utf-8")
    assert "ContrastMatrix" in stories_content
    assert "Light Mode" in stories_content
    assert "Dark Mode" in stories_content
    assert "bauhaus" in stories_content
    assert "dark-fantasy" in stories_content
    assert "parchment" in stories_content
    assert "cyber-rune" in stories_content


def test_file_lengths_under_500_lines():
    """Verify all touched frontend and UI service files comply strictly with the <500 lines limit."""
    all_files_to_check = COMPONENT_FILES + [
        APP_TS,
        HEADER_TS,
        CAMPAIGN_NAV_TS,
        THEMES_CSS,
        INDEX_CSS,
        INDEX_TS,
        PREVIEW_TS,
        CONTRAST_STORIES_TS,
        STORIES_TS,
        BOARD_TS,
        FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.ts",
        FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.styles.ts",
        FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.types.ts",
        FRONTEND_DIR / "src" / "stories" / "runefoble-settings-modal.stories.ts",
        REPO_ROOT / "services" / "voice_agent" / "ui" / "src" / "waveform-visualizer.ts",
        *THEME_SUBMODULES,
    ]

    seen = set()
    deduped = []
    for f in all_files_to_check:
        if f not in seen:
            seen.add(f)
            deduped.append(f)

    for file_path in deduped:
        assert file_path.is_file(), f"{file_path} must exist"
        lines = file_path.read_text(encoding="utf-8").splitlines()
        line_count = len(lines)
        assert line_count < 500, f"{file_path.name} has {line_count} lines, exceeding 500 limit"


def test_settings_modal_styles_modular_decomposition():
    """Verify settings modal CSS modular sub-modules, clean composite export, and line limits (TASK-0111)."""
    composite_file = FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.styles.ts"
    layout_file = FRONTEND_DIR / "src" / "components" / "styles" / "settings-modal-layout.styles.ts"
    tabs_file = FRONTEND_DIR / "src" / "components" / "styles" / "settings-modal-tabs.styles.ts"
    controls_file = (
        FRONTEND_DIR / "src" / "components" / "styles" / "settings-modal-controls.styles.ts"
    )
    dialog_alias_file = (
        FRONTEND_DIR / "src" / "components" / "styles" / "settings-modal-dialog.styles.ts"
    )

    assert composite_file.is_file(), "Composite styles file must exist"
    assert layout_file.is_file(), "Layout styles file must exist"
    assert tabs_file.is_file(), "Tabs styles file must exist"
    assert controls_file.is_file(), "Controls styles file must exist"
    assert dialog_alias_file.is_file(), "Dialog alias styles file must exist"

    # Line limits strictly under 150 lines per DoD
    for f in [composite_file, layout_file, tabs_file, controls_file, dialog_alias_file]:
        lines = len(f.read_text(encoding="utf-8").splitlines())
        assert lines < 150, f"{f.name} has {lines} lines, exceeding 150 limit"

    comp_content = composite_file.read_text(encoding="utf-8")
    assert "settingsModalStyles" in comp_content
    assert "layoutStyles" in comp_content
    assert "tabsStyles" in comp_content
    assert "controlsStyles" in comp_content

    layout_content = layout_file.read_text(encoding="utf-8")
    assert ".modal-overlay" in layout_content
    assert ".modal-dialog" in layout_content
    assert ".close-btn" in layout_content
    assert ".modal-footer" in layout_content

    tabs_content = tabs_file.read_text(encoding="utf-8")
    assert ".nav-tabs" in tabs_content
    assert ".tab-btn" in tabs_content
    assert ".theme-grid" in tabs_content
    assert ".theme-card" in tabs_content

    controls_content = controls_file.read_text(encoding="utf-8")
    assert ".swatch-group" in controls_content
    assert ".form-select" in controls_content
    assert ".checkbox-row" in controls_content


def test_themes_css_modular_decomposition():
    """Verify themes.css modular sub-modules, clean composite import, and line limits (TASK-0120)."""
    assert THEMES_CSS.is_file(), "themes.css root bundle must exist"
    content = THEMES_CSS.read_text(encoding="utf-8")

    # Verify standard CSS @import rules
    assert "@import './themes/base.css';" in content
    assert "@import './themes/bauhaus.css';" in content
    assert "@import './themes/dark-fantasy.css';" in content
    assert "@import './themes/parchment.css';" in content
    assert "@import './themes/cyber-rune.css';" in content

    # Verify root bundle line limit (< 40 lines per spec)
    root_lines = len(content.splitlines())
    assert root_lines < 40, f"themes.css has {root_lines} lines, exceeding 40 line limit"

    # Verify all modular sub-modules exist and are strictly under 150 lines
    for submodule in THEME_SUBMODULES:
        assert submodule.is_file(), f"{submodule.name} must exist"
        sub_lines = len(submodule.read_text(encoding="utf-8").splitlines())
        assert sub_lines < 150, f"{submodule.name} has {sub_lines} lines, exceeding 150 line limit"
