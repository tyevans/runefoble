"""Blackbox TDD tests for Silo S3 Media Asset Bucket Storage: Domain Events & OpenAPI.

Governed by:
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
- ADR-0003: UV Monorepo Workspace for Python Bounded Contexts
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
"""

from __future__ import annotations

from typing import Any

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from gateway_api.main import set_event_bus
from runefoble_events import AssetDeleted, AssetUploaded
from runefoble_platform.bus import bus as platform_bus
from runefoble_platform.redis_bus import MockAsyncRedis, RedisStreamsEventBus

from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES


@pytest.fixture(autouse=True)
def _isolate_storage(clean_storage_and_bus):
    """Ensure clean storage and bus before and after each test."""
    yield


# --- 1. Event Registration & CloudEvents Compliance Tests ---


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


# --- 2. Domain Event Dispatching (Redis Stream & In-Memory Bus) ---


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


# --- 3. OpenAPI Hub Registration ---


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
