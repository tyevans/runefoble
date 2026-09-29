"""Blackbox frontdoor tests for Frontend App Shell Test Suite Modular Decomposition (TASK-0287).

Governing ADRs: ADR-0004 (Lit Web Components), ADR-0012 (Bauhaus Modernism), ADR-0013 (Microfrontends).
Verifies:
1. Monolithic frontend/test/app-shell.test.ts is safely removed.
2. All modular test submodules exist under frontend/test/app_shell/:
   - routing.test.ts (< 110 lines, < 130 lines limit)
   - session-transitions.test.ts (< 110 lines, < 130 lines limit)
   - websocket-lifecycle.test.ts (< 100 lines, < 130 lines limit)
   - state-breadcrumbs.test.ts (< 100 lines, < 130 lines limit)
3. Each modular submodule executes cleanly via Node test runner with 0 failures.
4. Entire frontend test runner (npm test) executes and passes cleanly with 0 failures.
5. frontend/package.json test script properly covers test subdirectories.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
APP_SHELL_TEST_DIR = FRONTEND_DIR / "test" / "app_shell"
MONOLITHIC_TEST_FILE = FRONTEND_DIR / "test" / "app-shell.test.ts"
PACKAGE_JSON = FRONTEND_DIR / "package.json"

EXPECTED_SUBMODULES = {
    "routing.test.ts": 110,
    "session-transitions.test.ts": 110,
    "websocket-lifecycle.test.ts": 100,
    "state-breadcrumbs.test.ts": 100,
}


def test_monolithic_app_shell_test_removed():
    """Verify monolithic frontend/test/app-shell.test.ts has been safely removed."""
    assert not MONOLITHIC_TEST_FILE.exists(), (
        f"Monolithic test file {MONOLITHIC_TEST_FILE} must be safely removed"
    )


def test_modular_submodules_exist_and_satisfy_line_invariants():
    """Verify all 4 submodules exist and strictly satisfy line length limits (< 130 lines)."""
    assert APP_SHELL_TEST_DIR.is_dir(), f"{APP_SHELL_TEST_DIR} must exist as directory"

    for file_name, max_expected_lines in EXPECTED_SUBMODULES.items():
        file_path = APP_SHELL_TEST_DIR / file_name
        assert file_path.is_file(), f"Submodule {file_name} must exist"

        line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        assert line_count <= max_expected_lines, (
            f"{file_name} has {line_count} lines, exceeding target limit of {max_expected_lines}"
        )
        assert line_count < 130, (
            f"{file_name} has {line_count} lines, exceeding Hard Invariant 6 limit (< 130 lines)"
        )


def test_package_json_test_script_covers_submodules():
    """Verify frontend/package.json test script includes subdirectories."""
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    test_script = data.get("scripts", {}).get("test", "")
    assert "test/*/*.test.ts" in test_script or "test/**/*.test.ts" in test_script, (
        f"frontend/package.json test script must match nested test submodules, got: {test_script}"
    )


@pytest.mark.parametrize(
    "submodule_name,expected_tokens",
    [
        (
            "routing.test.ts",
            [
                "resolves login and registration views",
                "resolves campaign dashboard view",
                "resolves campaign detail view with extracted campaignId parameter",
                "resolves character roster view",
                "resolves session lobby view",
                "resolves active VTT session view",
                "defaults to campaigns view",
                "navigates to deep route",
            ],
        ),
        (
            "session-transitions.test.ts",
            [
                "transitions router from lobby to active VTT on launch-session event",
                "transitions router from lobby to active VTT upon incoming WebSocket session_started message",
                "dynamically populates lobby available characters",
                "prioritizes campaign-assigned character fallback",
                "creates character via createCharacter mutation",
                "assigns character to campaign and unassigns",
                "deletes character via deleteCharacter mutation",
            ],
        ),
        (
            "websocket-lifecycle.test.ts",
            [
                "activates WebSocket only on session-lobby and session-active routes",
                "tears down WebSocket when navigating away from an active session",
                "switches WebSocket connection when switching directly between sessions",
            ],
        ),
        (
            "state-breadcrumbs.test.ts",
            [
                "orchestrates active view state transitions across app sections",
                "updates breadcrumb trail dynamically on hierarchical navigation",
                "resolves dynamic entity titles asynchronously with caching",
                "verifies browser history and route state tracking on navigation",
            ],
        ),
    ],
)
def test_individual_submodule_execution(submodule_name: str, expected_tokens: list[str]):
    """Execute each modular test submodule independently and verify 0 failures."""
    submodule_path = APP_SHELL_TEST_DIR / submodule_name
    assert submodule_path.is_file()

    rel_path = str(submodule_path.relative_to(REPO_ROOT))
    result = subprocess.run(
        ["node", "--experimental-strip-types", "--test", rel_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Submodule {submodule_name} failed execution:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "fail 0" in result.stdout
    for token in expected_tokens:
        escaped_token = token.replace("#", "\\#")
        assert token in result.stdout or escaped_token in result.stdout, (
            f"Expected token '{token}' not found in {submodule_name} execution stdout:\n{result.stdout}"
        )


def test_frontend_npm_test_full_suite():
    """Verify npm test in frontend/ executes all suites with 100% pass rate."""
    result = subprocess.run(
        ["npm", "test"],
        cwd=FRONTEND_DIR,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"npm test in frontend failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "fail 0" in result.stdout
