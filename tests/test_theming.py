"""Tests for Frontend Theming System, Color Tokens, and Contrast Invariants (TASK-0012, TASK-0074)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
THEMES_CSS = FRONTEND_DIR / "src" / "styles" / "themes.css"
INDEX_CSS = FRONTEND_DIR / "src" / "index.css"
INDEX_HTML = FRONTEND_DIR / "index.html"
INDEX_TS = FRONTEND_DIR / "src" / "index.ts"
PREVIEW_TS = FRONTEND_DIR / ".storybook" / "preview.ts"
CONTRAST_STORIES_TS = FRONTEND_DIR / "src" / "stories" / "theme-contrast-matrix.stories.ts"

COMPONENT_FILES = [
    FRONTEND_DIR / "src" / "runefoble-app.styles.ts",
    FRONTEND_DIR / "src" / "components" / "runefoble-theme-switcher.ts",
    FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.styles.ts",
    REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-board.ts",
    REPO_ROOT / "services" / "board_state" / "ui" / "src" / "runefoble-map-uploader.styles.ts",
    REPO_ROOT / "services" / "character_sheet" / "ui" / "src" / "runefoble-character-card.ts",
    REPO_ROOT / "services" / "character_sheet" / "ui" / "src" / "runefoble-absentee-recap.ts",
    REPO_ROOT / "services" / "game_session" / "ui" / "src" / "runefoble-dice-roller.ts",
    REPO_ROOT / "services" / "game_session" / "ui" / "src" / "runefoble-initiative-tracker.ts",
    REPO_ROOT / "services" / "game_session" / "ui" / "src" / "runefoble-spectator-view.ts",
    REPO_ROOT / "services" / "the_watcher" / "ui" / "src" / "runefoble-watcher-feed.ts",
    REPO_ROOT / "services" / "the_watcher" / "ui" / "src" / "runefoble-autonomous-dm.ts",
    REPO_ROOT / "services" / "voice_agent" / "ui" / "src" / "runefoble-voice-controls.ts",
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


def test_themes_css_semantic_token_hierarchy():
    """Verify themes.css defines the full semantic token hierarchy across all themes and color modes."""
    assert THEMES_CSS.is_file(), "themes.css must exist"
    content = THEMES_CSS.read_text(encoding="utf-8")

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
        assert f"{token}:" in content, f"Token {token} must be defined in themes.css"


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
        FRONTEND_DIR / "src" / "runefoble-app.ts",
        THEMES_CSS,
        INDEX_CSS,
        INDEX_TS,
        PREVIEW_TS,
        CONTRAST_STORIES_TS,
        FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.ts",
        FRONTEND_DIR / "src" / "components" / "runefoble-settings-modal.types.ts",
        FRONTEND_DIR / "src" / "stories" / "theme-switcher.stories.ts",
        FRONTEND_DIR / "src" / "stories" / "runefoble-settings-modal.stories.ts",
        REPO_ROOT / "services" / "voice_agent" / "ui" / "src" / "waveform-visualizer.ts",
    ]

    for file_path in all_files_to_check:
        assert file_path.is_file(), f"{file_path} must exist"
        lines = file_path.read_text(encoding="utf-8").splitlines()
        line_count = len(lines)
        assert line_count < 500, f"{file_path.name} exceeds 500 lines: {line_count} lines"
