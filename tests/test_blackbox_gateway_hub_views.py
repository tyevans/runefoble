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

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app

REPO_ROOT = Path(__file__).resolve().parent.parent


def _auth(issuer, sub: str) -> dict[str, str]:
    """Return Bearer headers carrying a token that the gateway verifies for `sub`."""
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


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
    """Verify world atlas endpoint retrieves map layers, pins, and territories through gateway."""
    headers = _auth(signing_issuer, "dm_valeros")
    response = client.get(f"/api/v1/campaigns/{created_campaign_id}/atlas", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["campaign_id"] == created_campaign_id
    assert "pins" in data
    assert len(data["pins"]) >= 1
    assert data["pins"][0]["title"] == "Sunken Citadel"
    assert "territories" in data
    assert "layers" in data
    assert data["layers"]["continental"] is True

    # Unauthorized access check (Hard Invariant 1)
    unauthorized_res = client.get(
        f"/api/v1/campaigns/{created_campaign_id}/atlas",
        headers=_auth(signing_issuer, "stranger_bob"),
    )
    assert unauthorized_res.status_code == 403


def test_gateway_campaign_codex_frontdoors(
    client: TestClient, created_campaign_id: str, signing_issuer
) -> None:
    """Verify campaign codex endpoints retrieve lore entries through gateway."""
    headers = _auth(signing_issuer, "dm_valeros")

    # Base codex endpoint
    res1 = client.get(f"/api/v1/campaigns/{created_campaign_id}/codex", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["campaign_id"] == created_campaign_id
    assert "entries" in data1
    assert len(data1["entries"]) >= 1
    assert data1["entries"][0]["title"] == "The Star-Eater Relic"

    # Entries subpath endpoint
    res2 = client.get(f"/api/v1/campaigns/{created_campaign_id}/codex/entries", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["campaign_id"] == created_campaign_id
    assert len(data2["entries"]) >= 1

    # Unauthorized access check (Hard Invariant 1)
    unauthorized_res = client.get(
        f"/api/v1/campaigns/{created_campaign_id}/codex",
        headers=_auth(signing_issuer, "stranger_bob"),
    )
    assert unauthorized_res.status_code == 403


def test_gateway_campaign_analytics_frontdoors(
    client: TestClient, created_campaign_id: str, signing_issuer
) -> None:
    """Verify analytics telemetry endpoints (heatmap, MVP, timeline, summary) through gateway."""
    headers = _auth(signing_issuer, "dm_valeros")

    # Summary
    summary_res = client.get(f"/api/v1/analytics/campaigns/{created_campaign_id}", headers=headers)
    assert summary_res.status_code == 200
    assert summary_res.json()["campaign_id"] == created_campaign_id

    # Heatmap
    heatmap_res = client.get(
        f"/api/v1/analytics/campaigns/{created_campaign_id}/heatmap?session_id=session-tomb-14",
        headers=headers,
    )
    assert heatmap_res.status_code == 200
    heatmap = heatmap_res.json()
    assert heatmap["campaign_id"] == created_campaign_id
    assert heatmap["grid_cols"] == 8
    assert len(heatmap["cells"]) >= 2
    assert heatmap["cells"][0]["hit_count"] == 5

    # MVP and Performance
    mvp_res = client.get(
        f"/api/v1/analytics/campaigns/{created_campaign_id}/mvp?encounter_id=enc-crypt-1",
        headers=headers,
    )
    assert mvp_res.status_code == 200
    mvp = mvp_res.json()
    assert mvp["campaign_id"] == created_campaign_id
    assert mvp["overall_mvp"]["recipient_name"] == "Valeros"
    assert len(mvp["combatants"]) >= 2

    # Chronicle Timeline
    timeline_res = client.get(
        f"/api/v1/analytics/campaigns/{created_campaign_id}/timeline?session_id=session-tomb-14",
        headers=headers,
    )
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()
    assert timeline["campaign_id"] == created_campaign_id
    assert timeline["total_milestones"] >= 2
    assert "Breach of the Astral Crypt" in [m["title"] for m in timeline["milestones"]]

    # Unauthorized access check (Hard Invariant 1)
    unauthorized_res = client.get(
        f"/api/v1/analytics/campaigns/{created_campaign_id}/heatmap",
        headers=_auth(signing_issuer, "stranger_bob"),
    )
    assert unauthorized_res.status_code == 403


# ---------------------------------------------------------------------------
# 3. Router & App Shell Structural Integration
# ---------------------------------------------------------------------------
