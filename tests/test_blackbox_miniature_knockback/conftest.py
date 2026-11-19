"""Shared fixtures for miniature knockback and elevation physics blackbox tests (TASK-0171).

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0006: Redis Streams Distributed Domain Event Streaming
- ADR-0011: eventsource-py Core Event Sourcing
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Modular Microfrontend Decomposition
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
from tests.helpers.ws_identity import bearer

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def client(mock_bus: MockAsyncRedis, spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(board_app, headers=bearer("user-test"))
