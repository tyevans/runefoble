"""Blackbox test suite for Campaign Members Modular Styles Decomposition.

Part of TASK-0220 / ADR-0004 / ADR-0012 / ADR-0013.
Governed by:
- Hard Invariant 6: File length limit (<150 lines per style module, <500 lines source)
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
