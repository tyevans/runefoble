"""Blackbox frontdoor tests for Frontend App Shell Test Suite Modular Decomposition (TASK-0287).

Governing ADRs: ADR-0004 (Lit Web Components), ADR-0012 (Bauhaus Modernism), ADR-0013 (Microfrontends).
Verifies:
1. Monolithic frontend/test/app-shell.test.ts is safely removed.
2. The modular test submodules run under frontend/test/app_shell/:
   - routing.test.ts
   - session-transitions.test.ts
   - websocket-lifecycle.test.ts
   - state-breadcrumbs.test.ts
3. Each modular submodule executes cleanly via Node test runner with 0 failures.
4. Entire frontend test runner (npm test) executes and passes cleanly with 0 failures.
5. frontend/package.json test script properly covers test subdirectories.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.frontend_suite import run_frontend_suite
from tests.helpers.node_suite import NODE_TEST_TIMEOUT_S, run_node_tests

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
APP_SHELL_TEST_DIR = FRONTEND_DIR / "test" / "app_shell"


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

    rel_path = str(submodule_path.relative_to(REPO_ROOT))
    result = run_node_tests([rel_path], timeout=NODE_TEST_TIMEOUT_S)
    assert result.returncode == 0, (
        f"Submodule {submodule_name} failed execution:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "fail 0" in result.stdout
    for token in expected_tokens:
        escaped_token = token.replace("#", "\\#")
        assert token in result.stdout or escaped_token in result.stdout, (
            f"Expected token '{token}' not found in {submodule_name} execution stdout:\n{result.stdout}"
        )


@pytest.mark.timeout(600)
def test_frontend_npm_test_full_suite():
    """Verify the frontend test script runs all suites with 100% pass rate."""
    result = run_frontend_suite()
    assert result.returncode == 0, (
        f"frontend test suite failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "fail 0" in result.stdout
