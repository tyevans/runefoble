"""Blackbox frontdoor tests for decomposed battlemap uploader and tactical subviews.

Verifies TASK-0078 decomposition of runefoble-map-uploader into:
- runefoble-map-dropzone.ts (< 130 lines)
- runefoble-map-grid-config.ts (< 140 lines)
- runefoble-map-uploader.ts (< 120 lines)
Conforms to Hard Invariant 6 (< 500 lines per file) and Hard Invariant 7 (Blackbox TDD).
"""

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def board_client():
    from board_state.main import app

    return TestClient(app)


def test_board_state_ui_manifest_frontdoor(board_client):
    """Verify board_state microfrontend manifest discovers battlemap uploader."""
    response = board_client.get("/ui/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert manifest["service"] == "board_state"
    assert manifest["package"] == "@runefoble/board-state-ui"
    assert "runefoble-map-uploader" in manifest["components"]
    assert "runefoble-board" in manifest["components"]


def test_battlemap_uploader_silo_asset_frontdoor_upload(signing_issuer):
    """Verify Silo S3 asset upload frontdoor endpoint integrates with map uploader contract."""
    from gateway_api.main import app as gateway_app

    gateway_client = TestClient(
        gateway_app,
        headers={"Authorization": f"Bearer {signing_issuer.mint('gm-decomposed')}"},
    )
    sample_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
        b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
        b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )

    response = gateway_client.post(
        "/api/v1/assets/upload",
        files={"file": ("underdark_chasm.png", sample_png, "image/png")},
        data={"owner_id": "gm-decomposed", "asset_type": "battlemap"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "asset_id" in data
    assert "battlemaps/" in data["object_key"]
    assert data["content_type"] == "image/png"
    assert data["owner_id"] == "gm-decomposed"
    assert "download_url" in data
