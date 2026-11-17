"""Blackbox TDD frontdoor test suite for Campaign Hub Views and Gateway Alignment.

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
from gateway_api.campaign_store import campaign_store
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
    """Run campaign_lore and campaign_analytics stand-ins on loopback ports."""
    with (
        serve(_echo_upstream("campaign-lore")) as lore_url,
        serve(_echo_upstream("campaign-analytics")) as analytics_url,
    ):
        monkeypatch.setenv("CAMPAIGN_LORE_URL", lore_url)
        monkeypatch.setenv("CAMPAIGN_ANALYTICS_URL", analytics_url)
        yield


@pytest.fixture
def client(hub_upstreams) -> Iterator[TestClient]:
    """Run the gateway lifespan after the upstream URLs are set, so clients see them."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture(autouse=True)
def reset_store():
    campaign_store.reset()
    yield


@pytest.fixture
def created_campaign_id(client: TestClient, signing_issuer) -> str:
    """Create a campaign through the public frontdoor where dm_valeros is the Zanzibar owner."""
    res = client.post(
        "/api/v1/campaigns",
        json={
            "title": "Tomb of the Star-Eater",
            "setting": "Spelljammer Astral Void",
            "system": "5e",
            "description": "Exploration of the ancient stellar tomb.",
        },
        headers=_auth(signing_issuer, "dm_valeros"),
    )
    assert res.status_code == 201
    return res.json()["id"]


# ---------------------------------------------------------------------------
# 1. Hard Invariant 6: File Length Constraints
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 2. Gateway Hub Views: Atlas, Codex, and Analytics Frontdoors
# ---------------------------------------------------------------------------


def test_gateway_campaign_atlas_frontdoor(
    client: TestClient, created_campaign_id: str, signing_issuer
) -> None:
    """Verify the atlas route forwards the caller's bearer token to campaign_lore."""
    headers = _auth(signing_issuer, "dm_valeros")
    response = client.get(f"/api/v1/campaigns/{created_campaign_id}/atlas", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "campaign-lore"
    assert data["path"] == f"/api/v1/campaigns/{created_campaign_id}/atlas"
    assert data["authorization"] == headers["Authorization"]

    # Unauthorized access check (Hard Invariant 1)
    unauthorized_res = client.get(
        f"/api/v1/campaigns/{created_campaign_id}/atlas",
        headers=_auth(signing_issuer, "stranger_bob"),
    )
    assert unauthorized_res.status_code == 403


def test_gateway_campaign_codex_frontdoors(
    client: TestClient, created_campaign_id: str, signing_issuer
) -> None:
    """Verify both codex routes forward the bearer token to campaign_lore entries."""
    headers = _auth(signing_issuer, "dm_valeros")

    for route in ("codex", "codex/entries"):
        res = client.get(f"/api/v1/campaigns/{created_campaign_id}/{route}", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "campaign-lore"
        assert data["path"] == f"/api/v1/campaigns/{created_campaign_id}/codex/entries"
        assert data["authorization"] == headers["Authorization"]

    # Unauthorized access check (Hard Invariant 1)
    unauthorized_res = client.get(
        f"/api/v1/campaigns/{created_campaign_id}/codex",
        headers=_auth(signing_issuer, "stranger_bob"),
    )
    assert unauthorized_res.status_code == 403


def test_gateway_campaign_analytics_frontdoors(
    client: TestClient, created_campaign_id: str, signing_issuer
) -> None:
    """Verify analytics routes forward the bearer token and query parameters to campaign_analytics."""
    headers = _auth(signing_issuer, "dm_valeros")

    # Summary is served by the gateway itself.
    summary_res = client.get(f"/api/v1/analytics/campaigns/{created_campaign_id}", headers=headers)
    assert summary_res.status_code == 200
    assert summary_res.json()["campaign_id"] == created_campaign_id

    # Heatmap, MVP, and timeline are proxied with their query parameters.
    cases = [
        ("heatmap?session_id=session-tomb-14", "session_id", "session-tomb-14"),
        ("mvp?encounter_id=enc-crypt-1", "encounter_id", "enc-crypt-1"),
        ("timeline?session_id=session-tomb-14", "session_id", "session-tomb-14"),
    ]
    for route, key, value in cases:
        res = client.get(
            f"/api/v1/analytics/campaigns/{created_campaign_id}/{route}", headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "campaign-analytics"
        assert data["authorization"] == headers["Authorization"]
        assert data["query"] == {key: value}

    # Unauthorized access check (Hard Invariant 1)
    unauthorized_res = client.get(
        f"/api/v1/analytics/campaigns/{created_campaign_id}/heatmap",
        headers=_auth(signing_issuer, "stranger_bob"),
    )
    assert unauthorized_res.status_code == 403


# ---------------------------------------------------------------------------
# 3. Router & App Shell Structural Integration
# ---------------------------------------------------------------------------
