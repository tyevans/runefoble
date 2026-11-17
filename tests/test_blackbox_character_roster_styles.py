"""Blackbox test suite for Character Roster Modular Styles Decomposition.

Part of TASK-0222 / ADR-0004 / ADR-0012 / Hard Invariant 6.
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
