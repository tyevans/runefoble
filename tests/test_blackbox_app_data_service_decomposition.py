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
SERVICES_DIR = FRONTEND_DIR / "src" / "services"
APP_DATA_SERVICE_TS = SERVICES_DIR / "app-data-service.ts"
FIXTURES_TS = SERVICES_DIR / "app-data-service.fixtures.ts"
FALLBACK_DATA_TS = SERVICES_DIR / "fallback-data.ts"
TS_TEST_FILE = FRONTEND_DIR / "test" / "app-data-service-decomposition.test.ts"


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture(autouse=True)
def reset_stores():
    campaign_store.reset()
    character_store.reset()
    yield


def test_file_length_limits_and_decomposition():
    """Verify Hard Invariant 6: All files strictly satisfy line count constraints (<500 lines)."""
    files_to_check = [
        (APP_DATA_SERVICE_TS, 220),
        (FIXTURES_TS, 160),
        (FALLBACK_DATA_TS, 200),
        (Path(__file__), 500),
    ]

    for file_path, max_lines in files_to_check:
        assert file_path.is_file(), f"File {file_path} must exist"
        lines = len(file_path.read_text(encoding="utf-8").splitlines())
        assert lines < max_lines, f"{file_path.name} has {lines} lines (expected < {max_lines})"
        assert lines < 500, f"{file_path.name} exceeds global limit of 500 lines"


def test_fixtures_module_exports_and_contract():
    """Verify app-data-service.fixtures.ts exports all 5 core fallback arrays and helper functions."""
    fixtures_content = FIXTURES_TS.read_text(encoding="utf-8")

    assert "export const FALLBACK_CAMPAIGNS" in fixtures_content
    assert "export const FALLBACK_CHARACTERS" in fixtures_content
    assert "export const FALLBACK_MEMBERS" in fixtures_content
    assert "export const FALLBACK_PARTICIPANTS" in fixtures_content
    assert "export const FALLBACK_SESSIONS" in fixtures_content
    assert "export function getFallbackCampaignSessions" in fixtures_content
    assert "export function getFallbackSession" in fixtures_content


def test_app_data_service_modular_imports_and_reexports():
    """Verify app-data-service.ts imports from app-data-service.fixtures.ts and exposes public constants."""
    service_content = APP_DATA_SERVICE_TS.read_text(encoding="utf-8")

    assert "from './app-data-service.fixtures.ts'" in service_content
    assert "export { FALLBACK_CAMPAIGNS" in service_content
    assert "export class AppDataService" in service_content
    assert "export const appDataService = AppDataService.getInstance()" in service_content


def test_fallback_data_backward_compatibility():
    """Verify fallback-data.ts re-exports from app-data-service.fixtures.ts for backward compatibility."""
    fallback_content = FALLBACK_DATA_TS.read_text(encoding="utf-8")

    assert "from './app-data-service.fixtures.ts'" in fallback_content
    assert "export { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS }" in fallback_content
    assert "export function buildFallbackCharacterDetail" in fallback_content


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
    assert int(match.group(1)) >= 10, f"Expected at least 10 passed tests, got {match.group(1)}"
    assert "fail 0" in result.stdout
