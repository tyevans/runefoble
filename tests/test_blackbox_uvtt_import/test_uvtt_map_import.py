"""Blackbox integration tests for Universal VTT (.dd2vtt) map ingestion.

Governed by TASK-0193, ADR-0007, and ADR-0010.
"""

from __future__ import annotations

import json
from uuid import uuid4

from fastapi.testclient import TestClient
from runefoble_platform.storage import get_storage_service

from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES
from tests.test_blackbox_uvtt_import.conftest import build_sample_dd2vtt_dict


def test_blackbox_uvtt_multipart_file_upload(board_client: TestClient):
    """Verify importing a .dd2vtt file via multipart/form-data frontdoor."""
    board_id = f"camp-uvtt-{uuid4().hex[:8]}"
    uvtt_data = build_sample_dd2vtt_dict(cols=18, rows=14, pixels_per_grid=100)
    file_bytes = json.dumps(uvtt_data).encode("utf-8")

    # Frontdoor invocation: POST /api/v1/board/{id}/import/uvtt
    response = board_client.post(
        f"/api/v1/board/{board_id}/import/uvtt",
        files={"file": ("crypt_dungeon.dd2vtt", file_bytes, "application/json")},
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "imported"
    assert data["cols"] == 18
    assert data["rows"] == 14
    assert data["pixels_per_grid"] == 100
    assert len(data["wall_segments"]) == 3
    assert data["wall_segments"][0]["x1"] == 1.0
    assert data["wall_segments"][0]["y1"] == 1.0
    assert data["wall_segments"][0]["x2"] == 6.0
    assert data["wall_segments"][0]["y2"] == 1.0

    # Door portals & lights extraction
    assert len(data["portals"]) == 1
    assert data["portals"][0]["position"] == {"x": 3.5, "y": 1.0}
    assert data["portals"][0]["closed"] is True
    assert len(data["lights"]) == 1
    assert data["lights"][0]["range"] == 5.5

    # Background texture stored into Silo S3
    assert data["background_image_url"] is not None
    assert data["background_asset_id"] is not None
    storage = get_storage_service()
    asset = storage.get_asset_by_id(data["background_asset_id"])
    assert asset["content_type"] == "image/png"
    assert asset["byte_size"] == len(PNG_SAMPLE_BYTES)

    # Observable public projection check via GET /api/v1/boards/{board_id}
    get_res = board_client.get(f"/api/v1/boards/{board_id}")
    assert get_res.status_code == 200
    board_state = get_res.json()
    assert board_state["cols"] == 18
    assert board_state["rows"] == 14
    assert len(board_state["wall_segments"]) == 3
    assert board_state["background_image_url"] == data["background_image_url"]

    # Wall obstacle tokens placed within board boundaries
    obstacle_tokens = [
        t for t in board_state["tokens"].values() if t.get("token_type") == "obstacle"
    ]
    assert len(obstacle_tokens) >= 1
    coords = {(t["x"], t["y"]) for t in obstacle_tokens}
    assert (1, 1) in coords or (6, 1) in coords


def test_blackbox_uvtt_json_direct_payload(board_client: TestClient):
    """Verify importing a .dd2vtt map via raw JSON payload frontdoor."""
    board_id = f"board-{uuid4().hex[:8]}"
    uvtt_data = build_sample_dd2vtt_dict(cols=24, rows=18, pixels_per_grid=70)

    # Plural route alias frontdoor: POST /api/v1/boards/{id}/import/uvtt
    response = board_client.post(
        f"/api/v1/boards/{board_id}/import/uvtt",
        json=uvtt_data,
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "imported"
    assert data["cols"] == 24
    assert data["rows"] == 18
    assert len(data["wall_segments"]) == 3

    # Verify query projection
    get_res = board_client.get(f"/api/v1/boards/{board_id}")
    assert get_res.status_code == 200
    assert get_res.json()["cols"] == 24


def test_blackbox_uvtt_invalid_payload_error(board_client: TestClient):
    """Verify error handling on malformed UVTT data."""
    board_id = f"board-{uuid4().hex[:8]}"
    response = board_client.post(
        f"/api/v1/board/{board_id}/import/uvtt",
        content=b"not-valid-json-file-content",
        headers={"Content-Type": "application/octet-stream"},
    )
    assert response.status_code == 400
    assert "Invalid Universal VTT format" in response.json()["detail"]
