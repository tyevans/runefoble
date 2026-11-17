"""Tests for Component Token Invariants and WCAG Contrast Ratios (ADR-0004, ADR-0009, ADR-0012)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SERVICES_DIR = REPO_ROOT / "services"
THEMES_CSS = FRONTEND_DIR / "src" / "styles" / "themes.css"
COMPONENTS_DIR = FRONTEND_DIR / "src" / "components"
STYLES_DIR = COMPONENTS_DIR / "styles"


def resolve_css_imports(file_path: Path) -> str:
    """Recursively resolve CSS @import statements from the given stylesheet."""
    content = file_path.read_text(encoding="utf-8")
    base_dir = file_path.parent

    def replace_import(match: re.Match) -> str:
        imported_file = (base_dir / match.group(1)).resolve()
        return resolve_css_imports(imported_file) if imported_file.is_file() else match.group(0)

    return re.sub(r"""@import\s+['"]([^'"]+)['"]\s*;""", replace_import, content)


def srgb_to_lin(color_channel: int) -> float:
    c = color_channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_code: str) -> float:
    h = hex_code.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * srgb_to_lin(r) + 0.7152 * srgb_to_lin(g) + 0.0722 * srgb_to_lin(b)


def contrast(c1: str, c2: str) -> float:
    l1, l2 = luminance(c1), luminance(c2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def test_wcag_contrast_ratios_across_theme_matrix():
    """Verify WCAG 2.1 AA (min 4.5:1 for body) and AAA (min 7:1 for primary) contrast invariants."""
    content = resolve_css_imports(THEMES_CSS)
    blocks = re.findall(r"([^{]+)\{([^}]+)\}", content)

    checked_blocks = 0
    for selector, body in blocks:
        if "data-theme" in selector:
            vars_dict = dict(re.findall(r"(--rf-[a-z0-9\-]+):\s*([^;]+);", body))
            tp = vars_dict.get("--rf-text-primary", "").strip()
            ts = vars_dict.get("--rf-text-secondary", "").strip()
            bg_c = vars_dict.get("--rf-bg-canvas", "").strip()
            bg_s = vars_dict.get("--rf-bg-surface", "").strip()

            if tp.startswith("#") and bg_c.startswith("#"):
                ratio = contrast(tp, bg_c)
                assert ratio >= 7.0, f"Primary contrast in {selector.strip()}: {ratio:.2f} < 7.0"
                checked_blocks += 1

            if ts.startswith("#") and bg_c.startswith("#"):
                ratio = contrast(ts, bg_c)
                assert ratio >= 4.5, f"Secondary contrast in {selector.strip()}: {ratio:.2f} < 4.5"

            if tp.startswith("#") and bg_s.startswith("#"):
                ratio = contrast(tp, bg_s)
                assert ratio >= 7.0, f"Surface contrast in {selector.strip()}: {ratio:.2f} < 7.0"

    assert checked_blocks >= 8, f"Expected at least 8 theme/mode variations, found {checked_blocks}"
