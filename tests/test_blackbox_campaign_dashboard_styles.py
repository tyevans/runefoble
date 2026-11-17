"""Blackbox test suite for Campaign Dashboard Modular Styles Decomposition.

Part of TASK-0226 / ADR-0004 / ADR-0012 / ADR-0013.
Governed by:
- Hard Invariant 6: File length limit (<130 lines per style module, <500 lines source)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import json
from pathlib import Path


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
