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

from fastapi.testclient import TestClient

from tests.helpers.ws_identity import bearer


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
    client: TestClient, sample_stem_volumes: dict[str, float], soundscape_session_id: str
) -> None:
    """Verify POST /api/v1/soundscape/stems/volume updates individual stem channel sliders."""
    payload = {
        "session_id": soundscape_session_id,
        "stem_volumes": sample_stem_volumes,
    }
    resp = client.post("/api/v1/soundscape/stems/volume", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == soundscape_session_id
    for stem_name, vol in sample_stem_volumes.items():
        assert data["stem_channels"][stem_name] == vol


def test_rest_data_binding_tension_calculation(
    client: TestClient, sample_tension_payload: dict[str, Any]
) -> None:
    """Verify POST /api/v1/soundscape/tension/calculate computes tension metrics."""
    resp = client.post("/api/v1/soundscape/tension/calculate", json=sample_tension_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == sample_tension_payload["session_id"]
    assert data["tension_score"] >= 50
    assert data["stem_profile"] in ("tension", "combat", "boss")


def test_spicedb_zanzibar_authorization_on_soundscape_controls(
    client: TestClient, soundscape_session_id: str
) -> None:
    """Verify Zanzibar permissions guard DM mood overrides and controls."""
    payload = {
        "session_id": soundscape_session_id,
        "mood": "boss",
        "master_volume": 0.9,
    }

    # 1. A player without DM authority attempts a mood override -> 403 Forbidden
    resp_unauth = client.post(
        "/api/v1/soundscape/stems/override",
        headers=bearer("player-marcus"),
        json=payload,
    )
    assert resp_unauth.status_code == 403
    assert "Forbidden" in resp_unauth.json()["detail"]

    # 2. The campaign owner (the default client subject) overrides the mood -> 200 OK
    resp_auth = client.post("/api/v1/soundscape/stems/override", json=payload)
    assert resp_auth.status_code == 200
    data = resp_auth.json()
    assert data["stem_profile"] == "boss"
    assert data["manual_override"] is True
    assert data["master_volume"] == 0.9
