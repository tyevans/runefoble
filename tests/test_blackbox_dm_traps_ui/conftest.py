"""Shared fixtures for DM traps and map switcher UI blackbox tests (TASK-0159).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0012: Theming System and Accessibility Contrast Invariants
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from pathlib import Path

import pytest
from board_state.main import app as board_app
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(mock_bus: MockAsyncRedis, spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(board_app, headers=bearer("user-test"))
