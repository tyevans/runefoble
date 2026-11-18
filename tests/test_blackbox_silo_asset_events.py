"""Blackbox TDD tests for Silo S3 Media Asset Bucket Storage: Domain Events & OpenAPI.

Governed by:
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with frontdoor setup
- ADR-0003: UV Monorepo Workspace for Python Bounded Contexts
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
"""

from __future__ import annotations

import pytest
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_events.events import AssetDeleted, AssetUploaded

from tests.helpers.silo_fixtures import PNG_SAMPLE_BYTES

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

    # Class names are not identifiers: a retired short name resolves to no event
    assert get_event_class_or_none("AssetUploaded") is None
    assert get_event_class_or_none("AssetDeleted") is None

    # Verify CloudEvents 1.0 serialization
    upload_event = AssetUploaded(
        asset_id="asset-test-1",
        bucket="runefoble-assets",
        object_key="avatars/hero.png",
        content_type="image/png",
        byte_size=len(PNG_SAMPLE_BYTES),
        owner_id="user-42",
    )
    ce_dict = upload_event.to_cloudevent_dict()
    assert ce_dict["specversion"] == "1.0"
    assert ce_dict["type"] == "runefoble.events.asset.uploaded"
    assert ce_dict["source"] == f"/runefoble/asset/{upload_event.aggregate_id}"
    assert ce_dict["datacontenttype"] == "application/json"
    assert ce_dict["data"]["asset_id"] == "asset-test-1"
    assert ce_dict["data"]["byte_size"] == len(PNG_SAMPLE_BYTES)
    assert ce_dict["data"]["owner_id"] == "user-42"


# --- 2. Domain Event Dispatching (Redis Streams) ---


@pytest.mark.asyncio
async def test_blackbox_event_emission_on_upload_and_delete(
    trusted_ws_issuer, mock_bus, gateway_for
):
    """Verify AssetUploaded and AssetDeleted domain events are published on the Redis stream."""
    client = gateway_for(trusted_ws_issuer, "paladin_order")

    # 1. Perform upload
    upload_res = client.post(
        "/api/v1/assets/upload",
        files={"file": ("paladin_crest.png", PNG_SAMPLE_BYTES, "image/png")},
    )
    assert upload_res.status_code == 200
    asset_id = upload_res.json()["asset_id"]

    # Exactly one upload entry on the asset stream
    stream_events = mock_bus.streams.get("runefoble.events.asset", [])
    assert len(stream_events) == 1
    _evt_id, payload = stream_events[0]
    assert payload["event_type"] == "runefoble.events.asset.uploaded"
    assert asset_id in payload["payload"]
    assert "paladin_order" in payload["payload"]

    # 2. Perform delete
    del_res = client.delete(f"/api/v1/assets/{asset_id}")
    assert del_res.status_code == 200

    # Verify AssetDeleted in Redis stream
    assert len(stream_events) == 2
    _del_id, del_payload = stream_events[1]
    assert del_payload["event_type"] == "runefoble.events.asset.deleted"
    assert asset_id in del_payload["payload"]
    assert "paladin_order" in del_payload["payload"]


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
