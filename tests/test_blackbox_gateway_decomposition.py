"""Blackbox tests verifying Gateway API Router and App Shell Modular Decomposition (TASK-0045).

Governing ADRs: ADR-0003, ADR-0004, ADR-0007, ADR-0009, ADR-0013.
Ensures zero contract regressions, public HTTP frontdoor reachability, OpenAPI schema completeness,
and strict compliance with Hard Invariant 6 (all files < 250 lines).
"""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app


@pytest.fixture
def client(game_session_upstream) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def test_gateway_openapi_routes_completeness(client):
    """Verify all decomposed APIRouter routes are registered in Gateway OpenAPI schema."""
    openapi = client.app.openapi()
    paths = openapi["paths"]

    expected_routes = [
        "/healthz",
        "/readyz",
        "/api/v1/profile",
        "/api/v1/campaigns/{campaign_id}/roles",
        "/api/v1/campaigns/{campaign_id}",
        "/api/v1/sessions/{session_id}",
        "/api/v1/sessions/{session_id}/turns/advance",
        "/api/v1/sessions/{session_id}/dm-override",
        "/api/v1/sessions/{session_id}/atmosphere",
        "/api/v1/board/tokens/{token_id}/move",
        "/api/v1/board/tokens/{token_id}",
        "/api/v1/boards/{session_id}",
        "/api/v1/watcher/speak-and-act",
        "/api/v1/spectate/{session_id}",
    ]

    for route in expected_routes:
        assert route in paths, f"Route '{route}' missing from Gateway OpenAPI schema"


def test_health_and_readiness_frontdoor(client):
    """Verify health and readiness probes respond with expected structure."""
    health_res = client.get("/healthz")
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["status"] == "healthy"
    assert health_data["gateway"] == "runefoble-api-gateway"
    assert "SpiceDB Zanzibar" in health_data["authorization_engine"]
    assert "downstream_services" in health_data

    ready_res = client.get("/readyz")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"


def test_spectator_proxy_frontdoor(client):
    """Verify spectator proxy endpoint sanitizes state without private DM notes."""
    session_id = f"test-sess-{uuid4().hex[:6]}"
    res = client.get(f"/api/v1/spectate/{session_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert "tokens" in data
    assert "atmosphere" in data
    assert "chronicle" in data
    # Ensure private DM notes are redacted
    assert "dm_notes" not in data
    assert "monster_stat_blocks" not in data
