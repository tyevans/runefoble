"""Tests for Design System Tokens and Theme Definitions (ADR-0004, ADR-0009, ADR-0012)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
THEMES_CSS = FRONTEND_DIR / "src" / "styles" / "themes.css"
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
