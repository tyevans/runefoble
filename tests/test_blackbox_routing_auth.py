"""Blackbox TDD frontdoor test suite for Frontend Routing and Zitadel Auth.

Part of TASK-0214 / PRD-0023 / US-0062 / US-0066.
Governing ADRs:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limits (<250 lines for blackbox test, <500 lines overall)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.node_suite import NODE_TEST_TIMEOUT_S, run_node_tests

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
TESTS_DIR = FRONTEND_DIR / "tests"


@pytest.fixture
def client(game_session_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: Source File Line Count Constraints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 2. Node.js Blackbox Test Suite Execution (US-0062 & US-0066)
# ---------------------------------------------------------------------------


def test_node_blackbox_routing_auth_suite_execution() -> None:
    """Execute the Node-based TypeScript blackbox routing & auth test suite."""
    test_file = TESTS_DIR / "blackbox-routing-auth.test.ts"
    assert test_file.is_file(), f"{test_file} must exist"

    result = run_node_tests([test_file], timeout=NODE_TEST_TIMEOUT_S)
    assert result.returncode == 0, (
        f"Blackbox tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Router & Deep-Link Blackbox Tests (US-0066)" in result.stdout
    assert "Auth Guard & Session Persistence Tests (US-0062)" in result.stdout
    assert "fail 0" in result.stdout


# ---------------------------------------------------------------------------
# 3. Router & Auth Guard Declarations and Integration
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 4. Gateway Frontdoor Auth Endpoints Verification
# ---------------------------------------------------------------------------


def test_gateway_auth_frontdoors(client: TestClient, trusted_ws_issuer) -> None:
    """Verify Gateway API provides required frontdoor endpoints for auth workflows."""
    # Test authenticated profile retrieval with a signed bearer token. game_session serves the
    # profile and verifies the token itself (ADR-0015 c), so the issuer must be trusted there too.
    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('user-marcus')}"}
    res = client.get("/api/v1/profile", headers=headers)
    assert res.status_code == 200
    user_data = res.json()
    assert user_data["username"] == "user-marcus"
