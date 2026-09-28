"""Blackbox tests for Character Sheet Route and Inspector Subview Orchestration.

Governing ADRs: ADR-0004, ADR-0007, ADR-0012, ADR-0013.
Task Reference: TASK-0255.
Hard Invariants:
- Hard Invariant 6: File length limit (<500 lines).
- Hard Invariant 7: Blackbox TDD with frontdoor setup.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
ROUTER_TS = FRONTEND_DIR / "src" / "router" / "router.ts"
APP_TS = FRONTEND_DIR / "src" / "runefoble-app.ts"
APP_STYLES_TS = FRONTEND_DIR / "src" / "styles" / "app-shell.styles.ts"
DATA_SERVICE_TS = FRONTEND_DIR / "src" / "services" / "app-data-service.ts"
FALLBACK_DATA_TS = FRONTEND_DIR / "src" / "services" / "fallback-data.ts"
TEST_ROUTER_TS = FRONTEND_DIR / "test" / "router.test.ts"


def test_file_length_limits_and_decomposition():
    """Verify Hard Invariant 6: all modified files strictly satisfy line count constraints (<500 lines)."""
    files_to_check = [
        (ROUTER_TS, 250),
        (APP_TS, 250),
        (APP_STYLES_TS, 250),
        (DATA_SERVICE_TS, 450),
        (FALLBACK_DATA_TS, 200),
        (Path(__file__), 250),
    ]

    for file_path, max_lines in files_to_check:
        assert file_path.is_file(), f"{file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{file_path.name} has {lines} lines (expected < {max_lines})"
        assert lines < 500, f"{file_path.name} has {lines} lines (exceeds global 500 limit)"


def test_character_sheet_route_registration_and_api():
    """Verify router declares #/characters/:characterId and generates hierarchical breadcrumbs."""
    content = ROUTER_TS.read_text(encoding="utf-8")

    # Route pattern registered in STANDARD_ROUTES
    assert "'#/characters/:characterId'" in content

    # Breadcrumb generation logic
    assert "pattern === '#/characters/:characterId'" in content
    assert "this.resolveTitle('character', params.characterId)" in content
    assert "{ label: 'Home', path: '#/campaigns' }" in content
    assert "{ label: 'Characters', path: '#/characters' }" in content


def test_app_shell_view_orchestration_and_component_mounting():
    """Verify runefoble-app.ts declares 'character-sheet' view and mounts runefoble-character-sheet."""
    content = APP_TS.read_text(encoding="utf-8")

    # AppActiveView union includes character-sheet
    assert "'character-sheet'" in content

    # View detection in getActiveView()
    assert "pat.startsWith('#/characters/') && pat !== '#/characters'" in content

    # Component imports and mounting
    assert "@runefoble/character-sheet-ui" in content
    assert "<runefoble-character-sheet" in content
    assert "<runefoble-stand-in-guardrails" in content

    # Navigation back to roster
    assert "← Back to Roster" in content
    assert "router.navigate('#/characters')" in content

    # Character data binding
    assert ".characterId=${charId}" in content
    assert ".characterName=" in content
    assert ".characterClass=" in content
    assert ".currentHp=" in content
    assert ".maxHp=" in content
    assert ".armorClass=" in content
    assert ".equipment=" in content
    assert ".inventory=" in content
    assert ".conditions=" in content
    assert ".spellSlots=" in content

    # Route data loader fetches character
    assert "appDataService.fetchCharacter(charId)" in content


def test_app_data_service_character_fetch_and_fallbacks():
    """Verify appDataService exports fetchCharacter and getFallbackCharacterName."""
    service_content = DATA_SERVICE_TS.read_text(encoding="utf-8")
    assert "fetchCharacter(characterId: string)" in service_content
    assert "getFallbackCharacterName(id: string)" in service_content

    fallback_content = FALLBACK_DATA_TS.read_text(encoding="utf-8")
    assert "buildFallbackCharacterDetail" in fallback_content
    assert "FALLBACK_CHARACTERS" in fallback_content
    assert "char-valeros" in fallback_content
    assert "char-kyra" in fallback_content
    assert "char-ezren" in fallback_content


def test_character_sheet_styles_in_app_shell():
    """Verify Bauhaus CSS rules for character sheet subview and back button in app-shell.styles.ts."""
    content = APP_STYLES_TS.read_text(encoding="utf-8")

    assert ".character-sheet-view" in content
    assert ".character-sheet-header-bar" in content
    assert ".back-to-roster-btn" in content
    assert "--rf-bg-surface" in content
    assert "--rf-border-color" in content
    assert "--rf-accent-primary" in content


def test_node_router_unit_test_suite_execution():
    """Execute the Node-based TypeScript router unit test suite including character sheet route tests."""
    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(TEST_ROUTER_TS.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Router tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    match = re.search(r"pass (\d+)", result.stdout)
    assert match is not None, f"Could not find pass count in output: {result.stdout}"
    assert int(match.group(1)) >= 15, f"Expected at least 15 passed tests, got {match.group(1)}"
    assert "fail 0" in result.stdout
