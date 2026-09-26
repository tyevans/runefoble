"""Tests for Frontend Theming System and Bauhaus Modernist Default (TASK-0012)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
THEMES_CSS = FRONTEND_DIR / "src" / "styles" / "themes.css"
INDEX_CSS = FRONTEND_DIR / "src" / "index.css"
INDEX_HTML = FRONTEND_DIR / "index.html"
INDEX_TS = FRONTEND_DIR / "src" / "index.ts"
APP_TS = FRONTEND_DIR / "src" / "runefoble-app.ts"
SWITCHER_TS = FRONTEND_DIR / "src" / "components" / "runefoble-theme-switcher.ts"
BOARD_TS = FRONTEND_DIR / "src" / "components" / "runefoble-board.ts"
CARD_TS = FRONTEND_DIR / "src" / "components" / "runefoble-character-card.ts"
FEED_TS = FRONTEND_DIR / "src" / "components" / "runefoble-watcher-feed.ts"
STORIES_TS = FRONTEND_DIR / "src" / "stories" / "theme-switcher.stories.ts"


def test_themes_css_bauhaus_tokens():
    """Verify themes.css defines the Bauhaus Modernist default tokens."""
    assert THEMES_CSS.is_file(), "themes.css must exist"
    content = THEMES_CSS.read_text(encoding="utf-8")

    # Verify root / bauhaus selector
    assert ':root' in content
    assert '[data-theme="bauhaus"]' in content

    # Verify primary colors
    assert "--rf-color-red: #e63946;" in content
    assert "--rf-color-blue: #1d3557;" in content
    assert "--rf-color-yellow: #ffb703;" in content
    assert "--rf-color-dark: #121212;" in content
    assert "--rf-color-light: #ffffff;" in content

    # Verify surfaces and canvas
    assert "--rf-bg-canvas: #f8f9fa;" in content
    assert "--rf-bg-surface: #ffffff;" in content
    assert "--rf-bg-card: #ffffff;" in content

    # Verify borders and shadows
    assert "--rf-border-color: #121212;" in content
    assert "--rf-border-width: 2px;" in content
    assert "--rf-border-radius: 0px;" in content
    assert "--rf-shadow: 4px 4px 0px #121212;" in content
    assert "--rf-shadow-sm: 2px 2px 0px #121212;" in content

    # Verify typography and text
    assert "--rf-text-primary: #121212;" in content
    assert "--rf-text-muted: #4b5563;" in content

    # Verify accents
    assert "--rf-accent-primary: var(--rf-color-red);" in content
    assert "--rf-accent-secondary: var(--rf-color-blue);" in content
    assert "--rf-accent-tertiary: var(--rf-color-yellow);" in content


def test_themes_css_alternate_themes():
    """Verify themes.css defines dark-fantasy, parchment, and cyber-rune themes."""
    content = THEMES_CSS.read_text(encoding="utf-8")

    # Dark fantasy
    assert '[data-theme="dark-fantasy"]' in content
    assert "#0f172a" in content  # Obsidian canvas
    assert "#1e293b" in content  # Surface
    assert "#f59e0b" in content  # Gold accent
    assert "#8b5cf6" in content  # Rune purple accent
    assert "0 4px 12px rgba(0, 0, 0, 0.5)" in content

    # Parchment
    assert '[data-theme="parchment"]' in content
    assert "#f4ecd8" in content  # Aged paper canvas
    assert "#fff9eb" in content  # Surface
    assert "#5c3a21" in content  # Border & shadow
    assert "#2e1b0f" in content  # Dark ink text
    assert "#9b2226" in content  # Antique crimson
    assert "#bb8524" in content  # Brass
    assert "3px 3px 0px #5c3a21" in content

    # Cyber Rune
    assert '[data-theme="cyber-rune"]' in content
    assert "#09090b" in content  # Neon dark canvas
    assert "#18181b" in content  # Dark surface
    assert "#06b6d4" in content  # Neon cyan
    assert "#ec4899" in content  # Neon pink
    assert "#eab308" in content  # Neon yellow
    assert "0 0 10px rgba(6, 182, 212, 0.3)" in content


def test_frontend_index_css_and_html():
    """Verify index.css imports themes.css and uses theme tokens."""
    index_css = INDEX_CSS.read_text(encoding="utf-8")
    assert "@import './styles/themes.css';" in index_css
    assert "var(--rf-bg-canvas" in index_css
    assert "var(--rf-text-primary" in index_css

    index_html = INDEX_HTML.read_text(encoding="utf-8")
    assert 'rel="stylesheet" href="./src/index.css"' in index_html
    assert "<runefoble-app></runefoble-app>" in index_html


def test_theme_switcher_component():
    """Verify runefoble-theme-switcher Lit component implementation."""
    assert SWITCHER_TS.is_file(), "Theme switcher component must exist"
    content = SWITCHER_TS.read_text(encoding="utf-8")

    # Custom element registration
    assert "@customElement('runefoble-theme-switcher')" in content
    assert "class RunefobleThemeSwitcher extends LitElement" in content

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
    assert "import './styles/themes.css';" in app_content
    assert "<runefoble-theme-switcher></runefoble-theme-switcher>" in app_content
    assert "var(--rf-bg-canvas" in app_content
    assert "var(--rf-text-primary" in app_content
    assert "var(--rf-border-color" in app_content

    board_content = BOARD_TS.read_text(encoding="utf-8")
    assert "var(--rf-" in board_content
    assert "var(--rf-border-color" in board_content

    card_content = CARD_TS.read_text(encoding="utf-8")
    assert "var(--rf-" in card_content
    assert "var(--rf-bg-card" in card_content

    feed_content = FEED_TS.read_text(encoding="utf-8")
    assert "var(--rf-" in feed_content
    assert "var(--rf-shadow" in feed_content


def test_storybook_stories_exist():
    """Verify Storybook stories exist and contain theme variations."""
    assert STORIES_TS.is_file(), "theme-switcher.stories.ts must exist"
    content = STORIES_TS.read_text(encoding="utf-8")
    assert "Theme/RunefobleThemeSwitcher" in content
    assert "BauhausModernist" in content
    assert "DarkFantasy" in content
    assert "Parchment" in content
    assert "CyberRune" in content


def test_file_lengths_under_500_lines():
    """Verify all touched frontend files comply with the <500 lines limit."""
    files_to_check = [
        THEMES_CSS,
        INDEX_CSS,
        INDEX_TS,
        APP_TS,
        SWITCHER_TS,
        BOARD_TS,
        CARD_TS,
        FEED_TS,
        STORIES_TS,
    ]
    for file_path in files_to_check:
        assert file_path.is_file(), f"{file_path} must exist"
        lines = file_path.read_text(encoding="utf-8").splitlines()
        line_count = len(lines)
        assert line_count < 500, f"{file_path.name} exceeds 500 lines: {line_count} lines"
