"""Blackbox tests for Frontend SPA Client Router and Breadcrumb Navigation Chrome.

Governing ADRs: ADR-0004, ADR-0012, ADR-0013.
Task Reference: TASK-0206.
"""

from pathlib import Path

from tests.helpers.node_suite import NODE_TEST_TIMEOUT_S, run_node_tests

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
TEST_ROUTER_TS = FRONTEND_DIR / "test" / "router.test.ts"


def test_typescript_router_unit_test_suite_execution():
    """Execute the Node-based TypeScript router unit test suite."""
    import re

    assert TEST_ROUTER_TS.is_file()
    result = run_node_tests([TEST_ROUTER_TS], timeout=NODE_TEST_TIMEOUT_S)
    assert result.returncode == 0, (
        f"Router tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    match = re.search(r"pass (\d+)", result.stdout)
    assert match is not None, f"Could not find pass count in output: {result.stdout}"
    assert int(match.group(1)) >= 14, f"Expected at least 14 passed tests, got {match.group(1)}"
    assert "fail 0" in result.stdout
