"""Blackbox test suite for Character Roster Modular Styles Decomposition.

Part of TASK-0222 / ADR-0004 / ADR-0012 / Hard Invariant 6.
Governed by:
- Hard Invariant 6: File length limit (<130 lines per style module, <500 lines source)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def test_character_roster_style_module_file_lengths():
    """Verify aggregator < 50 lines and all extracted modules strictly < 130 lines."""
    repo_root = Path(__file__).resolve().parent.parent
    styles_dir = repo_root / "services" / "character_sheet" / "ui" / "src" / "roster" / "styles"
    aggregator = (
        repo_root
        / "services"
        / "character_sheet"
        / "ui"
        / "src"
        / "roster"
        / "runefoble-character-roster.styles.ts"
    )

    # 1. Aggregator must be < 50 lines (and within 40 lines budget per spec)
    assert aggregator.exists(), f"Aggregator {aggregator} does not exist"
    aggregator_lines = len(aggregator.read_text(encoding="utf-8").splitlines())
    assert aggregator_lines < 50, f"Aggregator exceeds 50 lines: {aggregator_lines} lines"
    assert aggregator_lines <= 40, f"Aggregator exceeds 40 lines budget: {aggregator_lines} lines"

    # 2. Each decomposed module must be strictly < 130 lines (and within specific budgets)
    expected_modules = {
        "roster_layout.styles.ts": 110,
        "character_card.styles.ts": 120,
        "assignment_dialog.styles.ts": 120,
        "index.ts": 50,
    }

    for filename, max_lines in expected_modules.items():
        module_path = styles_dir / filename
        assert module_path.exists(), f"Style module {module_path} does not exist"
        lines = len(module_path.read_text(encoding="utf-8").splitlines())
        assert lines < 130, f"Module {filename} violated Hard Invariant 6: {lines} lines >= 130"
        assert lines <= max_lines, (
            f"Module {filename} exceeded budget {max_lines}: got {lines} lines"
        )


def test_character_roster_style_content_and_tokens():
    """Verify key selectors, Bauhaus design tokens, and CSS properties exist without hardcoded hexes."""
    repo_root = Path(__file__).resolve().parent.parent
    styles_dir = repo_root / "services" / "character_sheet" / "ui" / "src" / "roster" / "styles"
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")

    layout_css = (styles_dir / "roster_layout.styles.ts").read_text(encoding="utf-8")
    assert ":host" in layout_css
    assert ".roster-container" in layout_css
    assert ".roster-header" in layout_css
    assert ".title-group" in layout_css
    assert ".btn" in layout_css
    assert ".btn-primary" in layout_css
    assert ".btn-secondary" in layout_css
    assert ".btn-danger" in layout_css
    assert ".controls-bar" in layout_css
    assert ".search-input" in layout_css
    assert ".filter-pills" in layout_css
    assert ".character-grid" in layout_css
    assert "--rf-font-family" in layout_css
    assert "--rf-text-primary" in layout_css
    assert not hex_pattern.findall(layout_css)

    card_css = (styles_dir / "character_card.styles.ts").read_text(encoding="utf-8")
    assert ".character-card" in card_css
    assert ".card-top" in card_css
    assert ".avatar-thumb" in card_css
    assert ".card-identity" in card_css
    assert ".card-name" in card_css
    assert ".card-class" in card_css
    assert ".card-level-badge" in card_css
    assert ".vitals-row" in card_css
    assert ".hp-header" in card_css
    assert ".hp-bar-bg" in card_css
    assert ".hp-bar-fill" in card_css
    assert ".stats-row" in card_css
    assert ".stat-chip" in card_css
    assert ".campaign-badge" in card_css
    assert ".card-actions" in card_css
    assert "--rf-accent-tertiary" in card_css
    assert not hex_pattern.findall(card_css)

    dialog_css = (styles_dir / "assignment_dialog.styles.ts").read_text(encoding="utf-8")
    assert ".empty-roster" in dialog_css
    assert ".empty-icon" in dialog_css
    assert ".modal-backdrop" in dialog_css
    assert ".assign-dialog" in dialog_css
    assert ".dialog-title" in dialog_css
    assert ".dialog-select" in dialog_css
    assert ".dialog-footer" in dialog_css
    assert "--rf-z-modal" in dialog_css
    assert not hex_pattern.findall(dialog_css)


def test_package_exports_and_component_wiring():
    """Verify package.json exports and component import wiring."""
    repo_root = Path(__file__).resolve().parent.parent
    pkg_json_path = repo_root / "services" / "character_sheet" / "ui" / "package.json"
    with open(pkg_json_path, encoding="utf-8") as f:
        pkg = json.load(f)

    exports = pkg.get("exports", {})
    assert "./roster/runefoble-character-roster.styles" in exports
    assert "./roster/styles" in exports
    assert "./roster/styles/roster_layout.styles" in exports
    assert "./roster/styles/character_card.styles" in exports
    assert "./roster/styles/assignment_dialog.styles" in exports

    # Verify component file imports styles and sets static styles
    comp_file = (
        repo_root
        / "services"
        / "character_sheet"
        / "ui"
        / "src"
        / "roster"
        / "runefoble-character-roster.ts"
    )
    comp_code = comp_file.read_text(encoding="utf-8")
    assert "characterRosterStyles" in comp_code
    assert "static styles = [characterRosterStyles]" in comp_code
