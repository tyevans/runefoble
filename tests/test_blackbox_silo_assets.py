"""Blackbox TDD tests for Silo S3 Media Asset Bucket Storage & Upload Pipeline.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All interactions and verifications happen strictly via public frontdoors:
- Public HTTP API endpoints in gateway_api (/api/v1/assets/...)
- Published standard domain events (AssetUploaded, AssetDeleted)
"""

from __future__ import annotations

import base64
from typing import Any

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus
from runefoble_events import AssetDeleted, AssetUploaded
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus
from runefoble_platform.storage import get_storage_service

# Sample 1x1 PNG bytes for testing image uploads
PNG_SAMPLE_BYTES: bytes = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02"
    b"\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)

# Sample WAV audio bytes for testing audio uploads
WAV_SAMPLE_BYTES: bytes = (
    b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00"
    b"\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
)


@pytest.fixture(autouse=True)
def clean_storage_and_bus():
    """Ensure isolated storage and bus states for each blackbox test."""
    storage = get_storage_service()
    storage.clear()
    set_event_bus(None)
    yield
    storage.clear()
    set_event_bus(None)


# ---------------------------------------------------------------------------
# 1. Event Registration & CloudEvents Compliance Tests
# ---------------------------------------------------------------------------


def test_asset_events_registration_and_cloudevents():
    """Verify AssetUploaded and AssetDeleted are registered in eventsource EventRegistry."""
    # Verify lookup by event type string
    uploaded_cls = get_event_class_or_none("runefoble.events.asset.uploaded")
    assert uploaded_cls is not None
    assert uploaded_cls is AssetUploaded

    deleted_cls = get_event_class_or_none("runefoble.events.asset.deleted")
    assert deleted_cls is not None
    assert deleted_cls is AssetDeleted

    # Verify lookup by class name
    assert get_event_class_or_none("AssetUploaded") is AssetUploaded
    assert get_event_class_or_none("AssetDeleted") is AssetDeleted

    # Verify CloudEvents 1.0 serialization
    upload_event = AssetUploaded(
        asset_id="asset-test-1",
        bucket="runefoble-assets",
        object_key="avatars/hero.png",
        content_type="image/png",
        byte_size=len(PNG_SAMPLE_BYTES),
        owner_id="user-42",
        url="http://silo:9000/runefoble-assets/avatars/hero.png",
    )
    ce_dict = upload_event.to_cloudevent_dict()
    assert ce_dict["specversion"] == "1.0"
    assert ce_dict["type"] == "runefoble.events.asset.uploaded"
    assert ce_dict["source"] == f"/runefoble/asset/{upload_event.aggregate_id}"
    assert ce_dict["datacontenttype"] == "application/json"
    assert ce_dict["data"]["asset_id"] == "asset-test-1"
    assert ce_dict["data"]["byte_size"] == len(PNG_SAMPLE_BYTES)
    assert ce_dict["data"]["owner_id"] == "user-42"


# ---------------------------------------------------------------------------
# 2. Blackbox Upload via Multipart/Form-Data & JSON Payloads
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 3. Retrieval, Direct Streaming, and Attachment Download
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 4. Validation Rejections (MIME Type, Max File Size, Empty Payload)
# ---------------------------------------------------------------------------


def test_blackbox_rejection_invalid_mime_type():
    """Verify rejection of non-whitelisted MIME types (e.g. text/plain, html)."""
    client = TestClient(gateway_app)

    # Attempt upload of disallowed text file
    response = client.post(
        "/api/v1/assets/upload",
        files={"file": ("script.sh", b"#!/bin/bash\necho hack", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported media MIME type" in response.json()["detail"]


def test_blackbox_rejection_oversize_payload():
    """Verify rejection of payloads exceeding 10MB limit."""
    client = TestClient(gateway_app)

    # 10MB + 1024 bytes
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


# ---------------------------------------------------------------------------
# 5. Deletion Lifecycle & Subsequent 404
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# 6. Domain Event Dispatching (Redis Stream & In-Memory Bus)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_blackbox_event_emission_on_upload_and_delete():
    """Verify AssetUploaded and AssetDeleted domain events are emitted to event buses."""
    mock_redis = MockAsyncRedis()
    mock_bus = RedisStreamsEventBus(client=mock_redis)
    set_event_bus(mock_bus)

    received_in_memory_events: list[Any] = []

    async def in_memory_upload_handler(event: Any):
        received_in_memory_events.append(event)

    platform_bus.subscribe("runefoble.events.asset.uploaded", in_memory_upload_handler)

    client = TestClient(gateway_app)

    # 1. Perform upload
    upload_res = client.post(
        "/api/v1/assets/upload",
        files={"file": ("paladin_crest.png", PNG_SAMPLE_BYTES, "image/png")},
        data={"owner_id": "paladin_order"},
    )
    assert upload_res.status_code == 200
    asset_id = upload_res.json()["asset_id"]

    # Check Redis stream events
    stream_events = mock_redis.streams.get("runefoble.events.asset", [])
    assert len(stream_events) >= 1
    _evt_id, payload = stream_events[0]
    assert payload["event_type"] == "runefoble.events.asset.uploaded"
    assert asset_id in payload["payload"]
    assert "paladin_order" in payload["payload"]

    # Check in-memory bus event
    assert len(received_in_memory_events) == 1
    mem_event = received_in_memory_events[0]
    assert isinstance(mem_event, AssetUploaded)
    assert mem_event.asset_id == asset_id
    assert mem_event.owner_id == "paladin_order"

    # 2. Perform delete
    del_res = client.delete(
        f"/api/v1/assets/{asset_id}",
        headers={"X-User-Id": "dm_cleanser"},
    )
    assert del_res.status_code == 200

    # Verify AssetDeleted in Redis stream
    assert len(stream_events) == 2
    _del_id, del_payload = stream_events[1]
    assert del_payload["event_type"] == "runefoble.events.asset.deleted"
    assert asset_id in del_payload["payload"]
    assert "dm_cleanser" in del_payload["payload"]


# ---------------------------------------------------------------------------
# 7. OpenAPI Hub Registration
# ---------------------------------------------------------------------------


def test_openapi_documentation_includes_asset_routes():
    """Verify that Swagger UI / OpenAPI docs hub exposes asset upload and query routes."""
    client = TestClient(gateway_app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json().get("paths", {})

    assert "/api/v1/assets/upload" in paths
    assert "post" in paths["/api/v1/assets/upload"]
    assert "/api/v1/assets/{asset_id}" in paths
    assert "/api/v1/assets/{asset_id}/stream" in paths
    assert "/api/v1/assets/{asset_id}/download" in paths
