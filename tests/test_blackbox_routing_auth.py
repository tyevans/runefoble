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

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SRC_DIR = FRONTEND_DIR / "src"
ROUTER_DIR = SRC_DIR / "router"
TESTS_DIR = FRONTEND_DIR / "tests"


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_store():
    campaign_store.reset()
    yield


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: Source File Line Count Constraints
# ---------------------------------------------------------------------------


def test_file_length_invariants() -> None:
    """Verify blackbox test suite and router files are strictly kept under size limits."""
    test_ts = TESTS_DIR / "blackbox-routing-auth.test.ts"
    assert test_ts.is_file(), f"{test_ts} must exist"
    test_lines = len(test_ts.read_text(encoding="utf-8").splitlines())
    assert test_lines < 250, (
        f"blackbox-routing-auth.test.ts has {test_lines} lines; must be < 250 lines"
    )

    auth_guard_ts = ROUTER_DIR / "auth-guard.ts"
    assert auth_guard_ts.is_file(), f"{auth_guard_ts} must exist"
    assert len(auth_guard_ts.read_text(encoding="utf-8").splitlines()) < 100

    app_ts = SRC_DIR / "runefoble-app.ts"
    assert app_ts.is_file(), f"{app_ts} must exist"
    assert len(app_ts.read_text(encoding="utf-8").splitlines()) < 250


# ---------------------------------------------------------------------------
# 2. Node.js Blackbox Test Suite Execution (US-0062 & US-0066)
# ---------------------------------------------------------------------------


def test_node_blackbox_routing_auth_suite_execution() -> None:
    """Execute the Node-based TypeScript blackbox routing & auth test suite."""
    test_file = TESTS_DIR / "blackbox-routing-auth.test.ts"
    assert test_file.is_file(), f"{test_file} must exist"

    result = subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "--test",
            str(test_file.relative_to(REPO_ROOT)),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Blackbox tests failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "Router & Deep-Link Blackbox Tests (US-0066)" in result.stdout
    assert "Auth Guard & Session Persistence Tests (US-0062)" in result.stdout
    assert "fail 0" in result.stdout


# ---------------------------------------------------------------------------
# 3. Router & Auth Guard Declarations and Integration
# ---------------------------------------------------------------------------


def test_auth_guard_and_router_wiring() -> None:
    """Verify router index exports auth guard and runefoble-app registers it."""
    router_index = (ROUTER_DIR / "index.ts").read_text(encoding="utf-8")
    assert "export * from './auth-guard.ts';" in router_index

    app_code = (SRC_DIR / "runefoble-app.ts").read_text(encoding="utf-8")
    assert "registerAuthGuard" in app_code
    assert "unlistenGuard" in app_code

    guard_code = (ROUTER_DIR / "auth-guard.ts").read_text(encoding="utf-8")
    assert "export function registerAuthGuard" in guard_code
    assert "targetRouter.beforeEach" in guard_code
    assert "auth.onAuthChanged" in guard_code


# ---------------------------------------------------------------------------
# 4. Gateway Frontdoor Auth Endpoints Verification
# ---------------------------------------------------------------------------


def test_gateway_auth_frontdoors(client: TestClient) -> None:
    """Verify Gateway API provides required frontdoor endpoints for auth workflows."""
    # Test authenticated profile retrieval with user header
    res = client.get("/api/v1/profile", headers={"X-User-Id": "user-marcus"})
    assert res.status_code == 200
    user_data = res.json()
    assert user_data["username"] == "user-marcus"
