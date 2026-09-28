"""Blackbox test suite for Campaign Dashboard Modular Styles Decomposition.

Part of TASK-0226 / ADR-0004 / ADR-0012 / ADR-0013.
Governed by:
- Hard Invariant 6: File length limit (<130 lines per style module, <500 lines source)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def test_campaign_dashboard_style_module_file_lengths():
    """Verify aggregator < 40 lines and all extracted modules strictly < 130 lines."""
    repo_root = Path(__file__).resolve().parent.parent
    styles_dir = (
        repo_root
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "campaigns"
        / "styles"
        / "dashboard"
    )
    aggregator = (
        repo_root
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "campaigns"
        / "runefoble-campaign-dashboard.styles.ts"
    )

    # 1. Aggregator must be < 40 lines per DoD
    assert aggregator.exists(), f"Aggregator {aggregator} does not exist"
    aggregator_lines = len(aggregator.read_text(encoding="utf-8").splitlines())
    assert aggregator_lines < 40, f"Aggregator exceeds 40 lines: {aggregator_lines} lines"

    # 2. Each decomposed module must be strictly < 130 lines (and within specific budgets)
    expected_modules = {
        "base.styles.ts": 110,
        "cards.styles.ts": 110,
        "modal.styles.ts": 120,
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


def test_campaign_dashboard_style_content_and_tokens():
    """Verify key selectors, Bauhaus design tokens, and CSS properties exist without hardcoded hexes."""
    repo_root = Path(__file__).resolve().parent.parent
    styles_dir = (
        repo_root
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "campaigns"
        / "styles"
        / "dashboard"
    )
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")

    base_css = (styles_dir / "base.styles.ts").read_text(encoding="utf-8")
    assert ":host" in base_css
    assert ".dashboard-header" in base_css
    assert ".header-titles" in base_css
    assert ".dashboard-title" in base_css
    assert ".dashboard-subtitle" in base_css
    assert ".controls-bar" in base_css
    assert ".filter-group" in base_css
    assert ".filter-chip" in base_css
    assert ".search-wrapper" in base_css
    assert ".search-input" in base_css
    assert ".btn-create-campaign" in base_css
    assert ".campaigns-grid" in base_css
    assert ".empty-state" in base_css
    assert ".empty-icon" in base_css
    assert ".empty-title" in base_css
    assert ".empty-desc" in base_css
    assert "--rf-font-family" in base_css
    assert "--rf-text-primary" in base_css
    assert not hex_pattern.findall(base_css)

    cards_css = (styles_dir / "cards.styles.ts").read_text(encoding="utf-8")
    assert ".campaign-card" in cards_css
    assert ".card-top" in cards_css
    assert ".card-title" in cards_css
    assert ".badges-row" in cards_css
    assert ".badge-live" in cards_css
    assert ".live-dot" in cards_css
    assert ".badge-role" in cards_css
    assert ".card-meta-line" in cards_css
    assert ".meta-tag" in cards_css
    assert ".card-desc" in cards_css
    assert ".card-footer" in cards_css
    assert ".dm-info" in cards_css
    assert ".player-info" in cards_css
    assert "--rf-accent-primary" in cards_css
    assert not hex_pattern.findall(cards_css)

    modal_css = (styles_dir / "modal.styles.ts").read_text(encoding="utf-8")
    assert ".modal-backdrop" in modal_css
    assert ".modal-card" in modal_css
    assert ".modal-header" in modal_css
    assert ".modal-title" in modal_css
    assert ".btn-close" in modal_css
    assert ".form-group" in modal_css
    assert ".form-label" in modal_css
    assert ".required-star" in modal_css
    assert ".form-input" in modal_css
    assert ".form-select" in modal_css
    assert ".form-textarea" in modal_css
    assert ".error-banner" in modal_css
    assert ".modal-actions" in modal_css
    assert ".btn-cancel" in modal_css
    assert ".btn-submit" in modal_css
    assert "--rf-z-modal" in modal_css
    assert not hex_pattern.findall(modal_css)


def test_package_exports_and_component_wiring():
    """Verify package.json exports and component import wiring."""
    repo_root = Path(__file__).resolve().parent.parent
    pkg_json_path = repo_root / "services" / "game_session" / "ui" / "package.json"
    with open(pkg_json_path, encoding="utf-8") as f:
        pkg = json.load(f)

    exports = pkg.get("exports", {})
    assert "./campaigns/dashboard" in exports
    assert "./campaigns/dashboard.styles" in exports
    assert "./campaigns/styles/dashboard" in exports

    # Verify component file imports styles and sets static styles
    comp_file = (
        repo_root
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "campaigns"
        / "runefoble-campaign-dashboard.ts"
    )
    comp_code = comp_file.read_text(encoding="utf-8")
    assert "campaignDashboardStyles" in comp_code
    assert "static styles = campaignDashboardStyles" in comp_code

    # Verify aggregator exports
    aggregator = (
        repo_root
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "campaigns"
        / "runefoble-campaign-dashboard.styles.ts"
    )
    agg_code = aggregator.read_text(encoding="utf-8")
    assert "baseStyles" in agg_code
    assert "cardStyles" in agg_code
    assert "modalStyles" in agg_code
    assert "campaignDashboardStyles" in agg_code
