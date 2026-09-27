"""Adaptive stem mixing and tension tests for Soundscape UI (TASK-0154).

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0007: API Gateway Architecture and Service Endpoints
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from soundscape.dependencies import set_spicedb_client


def test_rest_data_binding_catalog_and_foley_presets(client: TestClient) -> None:
    """Verify GET /api/v1/soundscape/stems lists layers, presets, and stem channels."""
    resp = client.get("/api/v1/soundscape/stems?session_id=sess-ui-01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-ui-01"
    assert "ambient" in data["stem_layers"]
    assert "combat" in data["stem_layers"]
    assert "thunder" in data["foley_presets"]
    assert "door_slam" in data["foley_presets"]
    assert "steel_clash" in data["foley_presets"]
    assert "roar" in data["foley_presets"]
    assert "stem_channels" in data
    assert "melody" in data["stem_channels"]
    assert "percussion" in data["stem_channels"]


def test_rest_data_binding_multi_channel_stem_volume_sliders(
    client: TestClient, sample_stem_volumes: dict[str, float]
) -> None:
    """Verify POST /api/v1/soundscape/stems/volume updates individual stem channel sliders."""
    payload = {
        "session_id": "sess-ui-01",
        "stem_volumes": sample_stem_volumes,
    }
    resp = client.post("/api/v1/soundscape/stems/volume", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-ui-01"
    for stem_name, vol in sample_stem_volumes.items():
        assert data["stem_channels"][stem_name] == vol


def test_rest_data_binding_tension_calculation(
    client: TestClient, sample_tension_payload: dict[str, Any]
) -> None:
    """Verify POST /api/v1/soundscape/tension/calculate computes tension metrics."""
    resp = client.post("/api/v1/soundscape/tension/calculate", json=sample_tension_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-ui-01"
    assert data["tension_score"] >= 50
    assert data["stem_profile"] in ("tension", "combat", "boss")


@pytest.mark.asyncio
async def test_spicedb_zanzibar_authorization_on_soundscape_controls(
    client: TestClient,
) -> None:
    """Verify Zanzibar permissions guard DM mood overrides and controls."""
    session_id = "sess-zanzibar-01"
    campaign_id = str(uuid4())
    dm_user = "dm-evelyn"
    player_user = "player-marcus"

    mock_db = MockSpiceDBClient()
    set_spicedb_client(mock_db)

    # 1. Player without DM authority attempts mood override -> 403 Forbidden
    resp_unauth = client.post(
        "/api/v1/soundscape/override",
        headers={"X-User-ID": player_user},
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "mood": "boss",
            "master_volume": 0.9,
        },
    )
    assert resp_unauth.status_code == 403
    assert "Forbidden" in resp_unauth.json()["detail"]

    # 2. Grant DM run_session permission in Zanzibar
    await mock_db.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="run_session",
        subject_type="user",
        subject_id=dm_user,
    )

    # 3. DM with permission performs mood override -> 200 OK
    resp_auth = client.post(
        "/api/v1/soundscape/override",
        headers={"X-User-ID": dm_user},
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "mood": "boss",
            "master_volume": 0.9,
        },
    )
    assert resp_auth.status_code == 200
    data = resp_auth.json()
    assert data["stem_profile"] == "boss"
    assert data["manual_override"] is True
    assert data["master_volume"] == 0.9
