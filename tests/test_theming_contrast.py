"""Tests for Component Token Invariants and WCAG Contrast Ratios (ADR-0004, ADR-0009, ADR-0012)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SERVICES_DIR = REPO_ROOT / "services"
THEMES_CSS = FRONTEND_DIR / "src" / "styles" / "themes.css"
COMPONENTS_DIR = FRONTEND_DIR / "src" / "components"
STYLES_DIR = COMPONENTS_DIR / "styles"

COMPONENT_FILES = [
    FRONTEND_DIR / "src" / "styles" / "app-shell.styles.ts",
    COMPONENTS_DIR / "runefoble-header.ts",
    COMPONENTS_DIR / "runefoble-campaign-nav.ts",
    COMPONENTS_DIR / "runefoble-theme-switcher.ts",
    STYLES_DIR / "settings-modal-layout.styles.ts",
    STYLES_DIR / "settings-modal-tabs.styles.ts",
    STYLES_DIR / "settings-modal-controls.styles.ts",
    SERVICES_DIR / "board_state" / "ui" / "src" / "runefoble-board.styles.ts",
    SERVICES_DIR / "board_state" / "ui" / "src" / "ghost_preview.styles.ts",
    SERVICES_DIR / "board_state" / "ui" / "src" / "runefoble-map-uploader.styles.ts",
    SERVICES_DIR / "character_sheet" / "ui" / "src" / "runefoble-character-card.ts",
    SERVICES_DIR / "character_sheet" / "ui" / "src" / "runefoble-absentee-recap.styles.ts",
    SERVICES_DIR / "game_session" / "ui" / "src" / "runefoble-dice-roller.ts",
    SERVICES_DIR / "game_session" / "ui" / "src" / "runefoble-initiative-tracker.styles.ts",
    SERVICES_DIR / "game_session" / "ui" / "src" / "runefoble-spectator-view.styles.ts",
    SERVICES_DIR / "the_watcher" / "ui" / "src" / "runefoble-watcher-feed.ts",
    SERVICES_DIR / "the_watcher" / "ui" / "src" / "runefoble-autonomous-dm.styles.ts",
    SERVICES_DIR / "voice_agent" / "ui" / "src" / "runefoble-voice-controls.styles.ts",
    SERVICES_DIR / "voice_agent" / "ui" / "src" / "runefoble-audio-indicator.ts",
]


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


def test_zero_hardcoded_hexes_in_web_components_static_styles():
    """Verify zero hardcoded hex color literals in Web Component static styles blocks."""
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")
    css_block_pattern = re.compile(r"(?:static\s+styles\s*=\s*css|css)`([\s\S]*?)`")

    for file_path in COMPONENT_FILES:
        assert file_path.is_file(), f"{file_path} must exist"
        matches = css_block_pattern.findall(file_path.read_text(encoding="utf-8"))
        assert len(matches) > 0, f"Expected CSS style block in {file_path.name}"
        for block in matches:
            hex_matches = hex_pattern.findall(block)
            assert not hex_matches, f"Found hardcoded hex {hex_matches} in {file_path.name}"


def test_components_adopt_tokens():
    """Verify components consume --rf-* tokens."""
    app = (FRONTEND_DIR / "src" / "runefoble-app.ts").read_text(encoding="utf-8")
    header = (COMPONENTS_DIR / "runefoble-header.ts").read_text(encoding="utf-8")
    styles = (FRONTEND_DIR / "src" / "styles" / "app-shell.styles.ts").read_text(encoding="utf-8")
    assert "import './styles/themes.css';" in app and "<runefoble-settings-modal" in app
    assert "settings-trigger" in header and "var(--rf-border-color" in header
    assert "var(--rf-bg-canvas" in styles and "var(--rf-text-primary" in styles

    board = (SERVICES_DIR / "board_state" / "ui" / "src" / "runefoble-board.styles.ts").read_text(
        encoding="utf-8"
    )
    assert "var(--rf-" in board and "var(--rf-border-color" in board

    card = (
        SERVICES_DIR / "character_sheet" / "ui" / "src" / "runefoble-character-card.ts"
    ).read_text(encoding="utf-8")
    assert "var(--rf-" in card and "var(--rf-bg-card" in card

    feed = (SERVICES_DIR / "the_watcher" / "ui" / "src" / "runefoble-watcher-feed.ts").read_text(
        encoding="utf-8"
    )
    assert "var(--rf-" in feed and "var(--rf-shadow" in feed

    voice = (
        SERVICES_DIR / "voice_agent" / "ui" / "src" / "runefoble-voice-controls.styles.ts"
    ).read_text(encoding="utf-8")
    assert "var(--rf-" in voice and "var(--rf-border-color" in voice


def test_settings_modal_styles_modular_decomposition():
    """Verify settings modal CSS modular sub-modules, clean composite export, and line limits (TASK-0111)."""
    sub_modules = [
        COMPONENTS_DIR / "runefoble-settings-modal.styles.ts",
        STYLES_DIR / "settings-modal-layout.styles.ts",
        STYLES_DIR / "settings-modal-tabs.styles.ts",
        STYLES_DIR / "settings-modal-controls.styles.ts",
        STYLES_DIR / "settings-modal-dialog.styles.ts",
    ]
    for f in sub_modules:
        assert f.is_file(), f"{f.name} must exist"
        lines = len(f.read_text(encoding="utf-8").splitlines())
        assert lines < 150, f"{f.name} has {lines} lines, exceeding 150 limit"

    comp, layout, tabs, controls = (f.read_text(encoding="utf-8") for f in sub_modules[:4])
    assert all(
        k in comp for k in ["settingsModalStyles", "layoutStyles", "tabsStyles", "controlsStyles"]
    )
    assert all(
        k in layout for k in [".modal-overlay", ".modal-dialog", ".close-btn", ".modal-footer"]
    )
    assert all(k in tabs for k in [".nav-tabs", ".tab-btn", ".theme-grid", ".theme-card"])
    assert all(k in controls for k in [".swatch-group", ".form-select", ".checkbox-row"])


def test_component_file_lengths_under_500_lines():
    """Verify all checked component and UI service files comply strictly with <500 lines limit."""
    all_files = COMPONENT_FILES + [
        FRONTEND_DIR / "src" / "runefoble-app.ts",
        COMPONENTS_DIR / "runefoble-settings-modal.ts",
        COMPONENTS_DIR / "runefoble-settings-modal.styles.ts",
        COMPONENTS_DIR / "runefoble-settings-modal.types.ts",
        FRONTEND_DIR / "src" / "stories" / "runefoble-settings-modal.stories.ts",
        SERVICES_DIR / "board_state" / "ui" / "src" / "runefoble-board.ts",
        SERVICES_DIR / "voice_agent" / "ui" / "src" / "waveform-visualizer.ts",
        Path(__file__),
    ]
    for file_path in set(all_files):
        assert file_path.is_file(), f"{file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < 500, f"{file_path.name} has {lines} lines, exceeding 500 limit"
