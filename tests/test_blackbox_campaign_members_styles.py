"""Blackbox test suite for Campaign Members Modular Styles Decomposition.

Part of TASK-0220 / ADR-0004 / ADR-0012 / ADR-0013.
Governed by:
- Hard Invariant 6: File length limit (<150 lines per style module, <500 lines source)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import json
from pathlib import Path


def test_campaign_members_style_module_file_lengths():
    """Verify aggregator < 50 lines and all extracted modules strictly < 150 lines."""
    repo_root = Path(__file__).resolve().parent.parent
    styles_dir = repo_root / "services" / "game_session" / "ui" / "src" / "campaigns" / "styles"
    aggregator = (
        repo_root
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "campaigns"
        / "runefoble-campaign-members.styles.ts"
    )

    # 1. Aggregator must be < 50 lines
    assert aggregator.exists(), f"Aggregator {aggregator} does not exist"
    aggregator_lines = len(aggregator.read_text(encoding="utf-8").splitlines())
    assert aggregator_lines < 50, f"Aggregator exceeds 50 lines: {aggregator_lines} lines"

    # 2. Each decomposed module must be strictly < 150 lines (and within specific budgets)
    expected_modules = {
        "base.styles.ts": 120,
        "roster.styles.ts": 120,
        "modal.styles.ts": 130,
        "badge.styles.ts": 90,
        "index.ts": 50,
    }

    for filename, max_lines in expected_modules.items():
        module_path = styles_dir / filename
        assert module_path.exists(), f"Style module {module_path} does not exist"
        lines = len(module_path.read_text(encoding="utf-8").splitlines())
        assert lines < 150, f"Module {filename} violated Hard Invariant 6: {lines} lines >= 150"
        assert lines <= max_lines, (
            f"Module {filename} exceeded budget {max_lines}: got {lines} lines"
        )


def test_campaign_members_style_content_and_tokens():
    """Verify key selectors, Bauhaus design tokens, and CSS properties exist."""
    repo_root = Path(__file__).resolve().parent.parent
    styles_dir = repo_root / "services" / "game_session" / "ui" / "src" / "campaigns" / "styles"

    base_css = (styles_dir / "base.styles.ts").read_text(encoding="utf-8")
    assert ":host" in base_css
    assert ".members-container" in base_css
    assert ".members-header" in base_css
    assert ".btn-invite" in base_css
    assert "--rf-accent-primary" in base_css

    roster_css = (styles_dir / "roster.styles.ts").read_text(encoding="utf-8")
    assert ".roster-card" in roster_css
    assert ".roster-list" in roster_css
    assert ".member-item" in roster_css
    assert ".avatar" in roster_css
    assert ".empty-state" in roster_css

    modal_css = (styles_dir / "modal.styles.ts").read_text(encoding="utf-8")
    assert ".modal-backdrop" in modal_css
    assert ".modal-card" in modal_css
    assert ".modal-header" in modal_css
    assert ".btn-close" in modal_css
    assert ".invite-link-row" in modal_css
    assert ".btn-copy" in modal_css
    assert ".btn-confirm-remove" in modal_css

    badge_css = (styles_dir / "badge.styles.ts").read_text(encoding="utf-8")
    assert ".badge-role" in badge_css
    assert ".role-select" in badge_css
    assert ".btn-remove" in badge_css


def test_package_exports_and_component_wiring():
    """Verify package.json exports and component import wiring."""
    repo_root = Path(__file__).resolve().parent.parent
    pkg_json_path = repo_root / "services" / "game_session" / "ui" / "package.json"
    with open(pkg_json_path, encoding="utf-8") as f:
        pkg = json.load(f)

    exports = pkg.get("exports", {})
    assert "./campaigns/members.styles" in exports
    assert "./campaigns/styles" in exports

    # Verify component file imports styles
    comp_file = (
        repo_root
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "campaigns"
        / "runefoble-campaign-members.ts"
    )
    comp_code = comp_file.read_text(encoding="utf-8")
    assert "campaignMembersStyles" in comp_code
