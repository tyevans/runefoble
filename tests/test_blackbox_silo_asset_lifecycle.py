"""Blackbox TDD tests for Silo S3 Media Asset Bucket Storage: Lifecycle & Validation.

Governed by:
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
- ADR-0003: UV Monorepo Workspace for Python Bounded Contexts
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
"""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES, WAV_SAMPLE_BYTES


@pytest.fixture(autouse=True)
def _isolate_storage(clean_storage_and_bus):
    """Ensure clean storage and bus before and after each test."""
    yield


# --- 1. Blackbox Upload via Multipart/Form-Data & JSON Payloads ---


def test_blackbox_upload_valid_image_multipart():
    """Verify uploading an avatar image via multipart/form-data frontdoor."""
    client = TestClient(gateway_app)
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": ("valeros_avatar.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"owner_id": "player-valeros", "asset_type": "avatar"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "asset_id" in data
    assert data["content_type"] == "image/png"
    assert data["byte_size"] == len(PNG_SAMPLE_BYTES)
    assert data["owner_id"] == "player-valeros"
    assert "valeros_avatar.png" in data["object_key"]
    assert "avatars/" in data["object_key"]
    assert "download_url" in data
    assert f"/api/v1/assets/{data['asset_id']}?stream=true" in data["download_url"]


def test_blackbox_upload_valid_battlemap_json_base64():
    """Verify uploading a tactical battlemap via JSON base64 frontdoor."""
    client = TestClient(gateway_app)
    b64_encoded = base64.b64encode(PNG_SAMPLE_BYTES).decode("utf-8")
    response = client.post(
        "/api/v1/assets/upload",
        json={
            "filename": "crypt_dungeon_grid.png",
            "content_type": "image/png",
            "data_base64": b64_encoded,
            "owner_id": "dm-alicia",
            "asset_type": "battlemap",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "asset_id" in data
    assert data["content_type"] == "image/png"
    assert data["owner_id"] == "dm-alicia"
    assert "battlemaps/" in data["object_key"]


def test_blackbox_upload_audio_asset():
    """Verify uploading an ambient audio track via multipart form-data."""
    client = TestClient(gateway_app)
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": ("ambient_crypt.wav", WAV_SAMPLE_BYTES, "audio/wav")},
        data={"owner_id": "dm-soundscape", "asset_type": "audio"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["content_type"] == "audio/wav"
    assert data["byte_size"] == len(WAV_SAMPLE_BYTES)
    assert "audios/" in data["object_key"]


# --- 2. Retrieval, Direct Streaming, and Attachment Download ---


def test_blackbox_get_asset_metadata_and_streaming():
    """Verify frontdoor metadata query, binary streaming, and download headers."""
    client = TestClient(gateway_app)

    # 1. Frontdoor upload
    upload_res = client.post(
        "/api/v1/assets/upload",
        files={"file": ("token_kyra.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"owner_id": "player-kyra"},
    )
    assert upload_res.status_code == 200
    asset_id = upload_res.json()["asset_id"]

    # 2. Get metadata
    meta_res = client.get(f"/api/v1/assets/{asset_id}")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert meta["asset_id"] == asset_id
    assert meta["content_type"] == "image/png"
    assert meta["owner_id"] == "player-kyra"

    # 3. Stream binary directly
    stream_res = client.get(f"/api/v1/assets/{asset_id}?stream=true")
    assert stream_res.status_code == 200
    assert stream_res.headers["content-type"].startswith("image/png")
    assert stream_res.content == PNG_SAMPLE_BYTES
    assert "inline" in stream_res.headers.get("content-disposition", "")

    # 4. Stream endpoint alias
    stream_alias = client.get(f"/api/v1/assets/{asset_id}/stream")
    assert stream_alias.status_code == 200
    assert stream_alias.content == PNG_SAMPLE_BYTES

    # 5. Download attachment endpoint
    download_res = client.get(f"/api/v1/assets/{asset_id}/download")
    assert download_res.status_code == 200
    assert download_res.content == PNG_SAMPLE_BYTES
    assert "attachment" in download_res.headers.get("content-disposition", "")


# --- 3. Validation Rejections (MIME Type, Max File Size, Empty Payload) ---


def test_blackbox_rejection_invalid_mime_type():
    """Verify rejection of non-whitelisted MIME types (e.g. text/plain, html)."""
    client = TestClient(gateway_app)
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": ("script.sh", b"#!/bin/bash\necho hack", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported media MIME type" in response.json()["detail"]


def test_blackbox_rejection_oversize_payload():
    """Verify rejection of payloads exceeding 10MB limit."""
    client = TestClient(gateway_app)
    oversize_bytes = b"0" * (10 * 1024 * 1024 + 1024)
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": ("huge_map.png", oversize_bytes, "image/png")},
    )
    assert response.status_code == 400
    assert "exceeds the maximum allowed limit" in response.json()["detail"]


def test_blackbox_rejection_empty_payload():
    """Verify rejection of empty asset payloads."""
    client = TestClient(gateway_app)
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


# --- 4. Deletion Lifecycle & Subsequent 404 ---


def test_blackbox_delete_asset_and_subsequent_404():
    """Verify asset deletion lifecycle and proper 404 responses for deleted items."""
    client = TestClient(gateway_app)

    # 1. Frontdoor upload
    upload_res = client.post(
        "/api/v1/assets/upload",
        files={"file": ("temporary_token.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"owner_id": "user-temporary"},
    )
    assert upload_res.status_code == 200
    asset_id = upload_res.json()["asset_id"]

    # 2. Delete asset via frontdoor
    del_res = client.delete(
        f"/api/v1/assets/{asset_id}",
        headers={"X-User-Id": "user-temporary"},
    )
    assert del_res.status_code == 200
    del_data = del_res.json()
    assert del_data["deleted"] is True
    assert del_data["asset_id"] == asset_id
    assert del_data["deleted_by"] == "user-temporary"

    # 3. Subsequent GET must return 404
    get_res = client.get(f"/api/v1/assets/{asset_id}")
    assert get_res.status_code == 404
    assert "not found" in get_res.json()["detail"]

    # 4. Subsequent DELETE must return 404
    del_again = client.delete(f"/api/v1/assets/{asset_id}")
    assert del_again.status_code == 404
