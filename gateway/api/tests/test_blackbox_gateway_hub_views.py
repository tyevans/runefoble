"""Blackbox TDD frontdoor test suite for Campaign Hub Views and Gateway Alignment.

Campaign Analytics views are covered in tests/test_blackbox_gateway_analytics_views.py (TASK-0588).

Governed by:
- TASK-0355: Campaign Hub Client Routing and View Orchestration for Codex, Atlas, and Telemetry
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0007: Domain-Driven Design and Bounded Contexts
- ADR-0012: Design System Theming and Bauhaus Modernism
- ADR-0013: Frontend Microfrontend Architecture
- Hard Invariant 1: SpiceDB Zanzibar schema authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import serve

REPO_ROOT = Path(__file__).resolve().parent.parent


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _echo_upstream(service: str) -> FastAPI:
    """Return a stand-in upstream that reports the headers and path it received."""
    app = FastAPI()

    @app.get("/{path:path}")
    def _echo(request: Request) -> dict[str, Any]:
        return {
            "service": service,
            "path": request.url.path,
            "query": dict(request.query_params),
            "authorization": request.headers.get("authorization"),
            "x_user_id": request.headers.get("x-user-id"),
        }

    return app


@pytest.fixture(autouse=True)
def hub_upstreams(monkeypatch) -> Iterator[None]:
    """Run a campaign_lore stand-in on a loopback port."""
    with serve(_echo_upstream("campaign-lore")) as lore_url:
        monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_LORE_URL", lore_url)
        yield


@pytest.fixture
def client(hub_upstreams, game_session_upstream) -> Iterator[TestClient]:
    """Run the gateway lifespan after the upstream URLs are set, so clients see them."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def created_campaign_id(client: TestClient, trusted_ws_issuer) -> str:
    """Create a campaign through the public frontdoor where dm_valeros is the Zanzibar owner."""
    res = client.post(
        "/api/v1/campaigns",
        json={
            "title": "Tomb of the Star-Eater",
            "setting": "Spelljammer Astral Void",
            "system": "5e",
            "description": "Exploration of the ancient stellar tomb.",
        },
        headers=_auth(trusted_ws_issuer, "dm_valeros"),
    )
    assert res.status_code == 201
    return res.json()["id"]


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: File Length Constraints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 2. Gateway Hub Views: Atlas and Codex Frontdoors
# ---------------------------------------------------------------------------


def test_gateway_campaign_atlas_frontdoor(
    client: TestClient, created_campaign_id: str, trusted_ws_issuer
) -> None:
    """Verify the atlas route forwards the caller's bearer token to campaign_lore."""
    headers = _auth(trusted_ws_issuer, "dm_valeros")
    response = client.get(f"/api/v1/campaigns/{created_campaign_id}/atlas", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "campaign-lore"
    assert data["path"] == f"/api/v1/campaigns/{created_campaign_id}/atlas"
    assert data["authorization"] == headers["Authorization"]
    # The owner checks `view` (Hard Invariant 1). The echo stand-in does not, so a denial is
    # tested against the real campaign_lore in test_blackbox_gateway_owner_permission_checks.py.


def test_gateway_campaign_codex_frontdoors(
    client: TestClient, created_campaign_id: str, trusted_ws_issuer
) -> None:
    """Verify the codex route forwards the bearer token to campaign_lore entries."""
    headers = _auth(trusted_ws_issuer, "dm_valeros")

    res = client.get(f"/api/v1/campaigns/{created_campaign_id}/codex", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["service"] == "campaign-lore"
    assert data["path"] == f"/api/v1/campaigns/{created_campaign_id}/codex/entries"
    assert data["authorization"] == headers["Authorization"]
    # The owner checks `view` (Hard Invariant 1). The echo stand-in does not, so a denial is
    # tested against the real campaign_lore in test_blackbox_gateway_owner_permission_checks.py.


# ---------------------------------------------------------------------------
# 3. Router & App Shell Structural Integration
# ---------------------------------------------------------------------------
