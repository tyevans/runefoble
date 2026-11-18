"""Shared fixtures for combat reaction prompt microfrontend blackbox tests (TASK-0158).

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
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(mock_bus: MockAsyncRedis, spicedb: MockSpiceDBClient, trusted_ws_issuer) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )
