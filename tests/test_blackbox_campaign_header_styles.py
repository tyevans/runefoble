"""Blackbox test suite for Campaign Header Modular Styles Decomposition.

Part of TASK-0269 / ADR-0004 / ADR-0012 / ADR-0013.
Governed by:
- Hard Invariant 6: File length limit (<150 lines per style module, <500 lines source)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def test_campaign_header_style_module_file_lengths():
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
        / "runefoble-campaign-header.styles.ts"
    )

    # 1. Aggregator must be < 50 lines (and within 40 lines per spec)
    assert aggregator.exists(), f"Aggregator {aggregator} does not exist"
    aggregator_lines = len(aggregator.read_text(encoding="utf-8").splitlines())
    assert aggregator_lines < 50, f"Aggregator exceeds 50 lines: {aggregator_lines} lines"
    assert aggregator_lines <= 40, f"Aggregator exceeds 40 lines budget: {aggregator_lines} lines"

    # 2. Each decomposed module must be strictly < 150 lines (and within specific budgets)
    expected_modules = {
        "header_hero.styles.ts": 120,
        "header_meta.styles.ts": 130,
        "header_actions.styles.ts": 130,
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


def test_campaign_header_style_content_and_tokens():
    """Verify key selectors, Bauhaus design tokens, and CSS properties exist without hardcoded hexes."""
    repo_root = Path(__file__).resolve().parent.parent
    styles_dir = repo_root / "services" / "game_session" / "ui" / "src" / "campaigns" / "styles"
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,8}")

    hero_css = (styles_dir / "header_hero.styles.ts").read_text(encoding="utf-8")
    assert ":host" in hero_css
    assert ".campaign-header-card" in hero_css
    assert ".hero-banner" in hero_css
    assert ".cover-image" in hero_css
    assert ".hero-banner-fallback" in hero_css
    assert ".geometric-pattern" in hero_css
    assert ".geometric-accent-circle" in hero_css
    assert ".geometric-accent-bar" in hero_css
    assert ".fallback-hero-title" in hero_css
    assert "--rf-accent-primary" in hero_css
    assert not hex_pattern.findall(hero_css)

    meta_css = (styles_dir / "header_meta.styles.ts").read_text(encoding="utf-8")
    assert ".header-content" in meta_css
    assert ".meta-badges-row" in meta_css
    assert ".badge" in meta_css
    assert ".badge-system" in meta_css
    assert ".badge-setting" in meta_css
    assert ".badge-status" in meta_css
    assert ".badge-dm-profile" in meta_css
    assert ".dm-avatar" in meta_css
    assert ".campaign-title" in meta_css
    assert ".campaign-description" in meta_css
    assert "--rf-border-color" in meta_css
    assert not hex_pattern.findall(meta_css)

    actions_css = (styles_dir / "header_actions.styles.ts").read_text(encoding="utf-8")
    assert ".title-action-row" in actions_css
    assert ".btn-edit-campaign" in actions_css
    assert ".modal-backdrop" in actions_css
    assert ".modal-card" in actions_css
    assert ".modal-header" in actions_css
    assert ".btn-close" in actions_css
    assert ".form-group" in actions_css
    assert ".btn-cancel" in actions_css
    assert ".btn-submit" in actions_css
    assert "--rf-accent-primary" in actions_css
    assert not hex_pattern.findall(actions_css)


def test_package_exports_and_component_wiring():
    """Verify package.json exports and component import wiring."""
    repo_root = Path(__file__).resolve().parent.parent
    pkg_json_path = repo_root / "services" / "game_session" / "ui" / "package.json"
    with open(pkg_json_path, encoding="utf-8") as f:
        pkg = json.load(f)

    exports = pkg.get("exports", {})
    assert "./campaigns/header" in exports
    assert "./campaigns/header.styles" in exports
    assert "./campaigns/styles" in exports

    # Verify component file imports styles and sets static styles
    comp_file = (
        repo_root
        / "services"
        / "game_session"
        / "ui"
        / "src"
        / "campaigns"
        / "runefoble-campaign-header.ts"
    )
    comp_code = comp_file.read_text(encoding="utf-8")
    assert "campaignHeaderStyles" in comp_code
    assert "static styles = campaignHeaderStyles" in comp_code
