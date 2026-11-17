"""Blackbox frontdoor test suite for AppDataService Fixtures and Client Modular Decomposition.

Governing ADRs: ADR-0004, ADR-0007.
Task Reference: TASK-0271.
Hard Invariants:
- Hard Invariant 6: File length limit (<500 lines; app-data-service < 220, fixtures < 160)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.character_store import character_store
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
TS_TEST_FILE = FRONTEND_DIR / "test" / "app-data-service.test.ts"


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_stores():
    campaign_store.reset()
    character_store.reset()
    yield


def test_frontend_node_blackbox_suite_execution():
    """Execute the Node-based TypeScript blackbox test suite for TASK-0271 and assert 100% pass."""
    assert TS_TEST_FILE.is_file(), f"Frontend test suite {TS_TEST_FILE} must exist"

    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(TS_TEST_FILE.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Frontend blackbox suite failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    match = re.search(r"pass (\d+)", result.stdout)
    assert match is not None, f"Could not find pass count in output: {result.stdout}"
    assert int(match.group(1)) >= 20, f"Expected at least 20 passed tests, got {match.group(1)}"
    assert "fail 0" in result.stdout
