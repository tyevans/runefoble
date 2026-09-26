"""Tests for Design System Tokens and Theme Definitions (ADR-0004, ADR-0009, ADR-0012)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
THEMES_CSS = FRONTEND_DIR / "src" / "styles" / "themes.css"
THEME_SUBMODULES = [
    FRONTEND_DIR / "src" / "styles" / "themes" / f"{name}.css"
    for name in ["base", "bauhaus", "dark-fantasy", "parchment", "cyber-rune"]
]
INDEX_CSS = FRONTEND_DIR / "src" / "index.css"
INDEX_HTML = FRONTEND_DIR / "index.html"
INDEX_TS = FRONTEND_DIR / "src" / "index.ts"
SWITCHER_TS = FRONTEND_DIR / "src" / "components" / "runefoble-theme-switcher.ts"
STORIES_TS = FRONTEND_DIR / "src" / "stories" / "theme-switcher.stories.ts"
PREVIEW_TS = FRONTEND_DIR / ".storybook" / "preview.ts"
CONTRAST_STORIES_TS = FRONTEND_DIR / "src" / "stories" / "theme-contrast-matrix.stories.ts"

REQUIRED_SEMANTIC_TOKENS = [
    "--rf-bg-canvas",
    "--rf-bg-surface",
    "--rf-bg-surface-elevated",
    "--rf-bg-card",
    "--rf-bg-inset",
    "--rf-text-primary",
    "--rf-text-secondary",
    "--rf-text-muted",
    "--rf-text-inverse",
    "--rf-border-color",
    "--rf-border-subtle",
    "--rf-border-focus",
    "--rf-shadow-color",
    "--rf-shadow",
    "--rf-shadow-sm",
]


def resolve_css_imports(file_path: Path) -> str:
    """Recursively resolve CSS @import statements from the given stylesheet."""
    content = file_path.read_text(encoding="utf-8")
    base_dir = file_path.parent

    def replace_import(match: re.Match) -> str:
        imported_file = (base_dir / match.group(1)).resolve()
        return resolve_css_imports(imported_file) if imported_file.is_file() else match.group(0)

    return re.sub(r"""@import\s+['"]([^'"]+)['"]\s*;""", replace_import, content)


def test_themes_css_semantic_token_hierarchy():
    """Verify themes.css defines the full semantic token hierarchy across all themes and color modes."""
    assert THEMES_CSS.is_file(), "themes.css must exist"
    content = resolve_css_imports(THEMES_CSS)

    selectors = [":root", '[data-color-mode="light"]', '[data-color-mode="dark"]']
    for selector in [*selectors, "@media (prefers-color-scheme: dark)"]:
        assert selector in content

    for theme in ["bauhaus", "dark-fantasy", "parchment", "cyber-rune"]:
        assert f'[data-theme="{theme}"]' in content
        assert (
            f'[data-theme="{theme}"][data-color-mode="light"]' in content
            or f'[data-theme="{theme}"]' in content
        )
        assert f'[data-theme="{theme}"][data-color-mode="dark"]' in content

    for token in REQUIRED_SEMANTIC_TOKENS:
        assert token in content, f"Missing required semantic token {token} in themes.css"

    assert (
        "--rf-border-width" in content
        and "--rf-shadow:" in content
        and "--rf-shadow-sm:" in content
    )


def test_themes_css_modular_decomposition():
    """Verify themes.css modular sub-modules, clean composite import, and line limits (TASK-0120)."""
    assert THEMES_CSS.is_file(), "themes.css root bundle must exist"
    content = THEMES_CSS.read_text(encoding="utf-8")

    for name in ["base", "bauhaus", "dark-fantasy", "parchment", "cyber-rune"]:
        assert f"@import './themes/{name}.css';" in content

    assert len(content.splitlines()) < 40, "themes.css exceeds 40 line limit"
    for submodule in THEME_SUBMODULES:
        assert submodule.is_file(), f"{submodule.name} must exist"
        lines = len(submodule.read_text(encoding="utf-8").splitlines())
        assert lines < 150, f"{submodule.name} has {lines} lines, exceeding 150 line limit"


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

    assert "runefoble-theme" in content
    assert "localStorage" in content
    assert "document.documentElement.setAttribute('data-theme', theme)" in content
    assert "theme-changed" in content

    for mode in ["bauhaus", "dark-fantasy", "parchment", "cyber-rune"]:
        assert f"'{mode}'" in content

    index_ts = INDEX_TS.read_text(encoding="utf-8")
    assert "export * from './components/runefoble-theme-switcher.ts';" in index_ts


def test_storybook_stories_exist():
    """Verify Storybook stories exist and contain theme variations."""
    assert STORIES_TS.is_file(), "theme-switcher.stories.ts must exist"
    content = STORIES_TS.read_text(encoding="utf-8")
    for key in [
        "Theme/RunefobleThemeSwitcher",
        "BauhausModernist",
        "DarkFantasy",
        "Parchment",
        "CyberRune",
    ]:
        assert key in content


def test_storybook_color_mode_and_theme_matrix():
    """Verify Storybook toolbar preview configuration and side-by-side theme contrast stories."""
    assert PREVIEW_TS.is_file(), "Storybook preview.ts must exist"
    preview = PREVIEW_TS.read_text(encoding="utf-8")
    for exp in ["colorMode:", "theme:", "'light'", "'dark'", "'system'", "data-color-mode"]:
        assert exp in preview

    assert CONTRAST_STORIES_TS.is_file(), "theme-contrast-matrix.stories.ts must exist"
    stories = CONTRAST_STORIES_TS.read_text(encoding="utf-8")
    for exp in [
        "ContrastMatrix",
        "Light Mode",
        "Dark Mode",
        "bauhaus",
        "dark-fantasy",
        "parchment",
        "cyber-rune",
    ]:
        assert exp in stories


def test_theme_token_file_lengths():
    """Verify theme token stylesheets and preview configs comply with the <500 lines limit."""
    files = [
        THEMES_CSS,
        INDEX_CSS,
        INDEX_TS,
        PREVIEW_TS,
        STORIES_TS,
        CONTRAST_STORIES_TS,
        SWITCHER_TS,
        Path(__file__),
        *THEME_SUBMODULES,
    ]
    for file_path in set(files):
        assert file_path.is_file(), f"{file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < 500, f"{file_path.name} has {lines} lines, exceeding 500 limit"
