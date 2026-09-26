"""Tests for TASK-0071: WebSocket Zanzibar Connection Handshake Authorization."""

import asyncio

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient
from gateway_api.auth import get_spicedb_client, set_spicedb_client
from gateway_api.main import app, set_event_bus
from runefoble_auth.spicedb import MockSpiceDBClient, SpiceDBClient


@pytest.fixture(autouse=True)
def reset_state():
    """Reset SpiceDB client and event bus before and after each test."""
    client = MockSpiceDBClient()
    set_spicedb_client(client)
    set_event_bus(None)
    yield
    set_spicedb_client(SpiceDBClient())
    set_event_bus(None)


def _grant(resource_type: str, resource_id: str, relation: str, subject_id: str) -> None:
    asyncio.run(
        get_spicedb_client().write_relationship(
            resource_type, resource_id, relation, "user", subject_id
        )
    )


def test_connecting_with_valid_campaign_viewer_permissions():
    """Verify connecting with valid campaign viewer/reader permissions succeeds."""
    campaign_id = "camp-connect-view"
    client = TestClient(app)

    # 1. User with 'view' permission can connect
    _grant("campaign", campaign_id, "view", "viewer_alice")
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id=viewer_alice") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["campaign_id"] == campaign_id
        assert msg["user_id"] == "viewer_alice"

    # 2. User with 'read' permission can connect
    _grant("campaign", campaign_id, "read", "reader_bob")
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id=reader_bob") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["user_id"] == "reader_bob"


def test_connecting_with_unauthorized_subject():
    """Verify connecting with unauthorized subject is rejected with PERMISSION_DENIED and closed with 4003."""
    campaign_id = "camp-connect-unauth"
    client = TestClient(app)

    # Stranger has no relations in SpiceDB
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id=stranger_joe") as ws:
        err_msg = ws.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "PERMISSION_DENIED"
        assert err_msg["action"] == "connect"
        assert "insufficient permissions" in err_msg["message"]

        # Subsequent receive raises WebSocketDisconnect with 4003
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4003


def test_dynamic_permission_revocation_rejects_reconnect():
    """Verify dynamically deleting Zanzibar permission revokes connection privileges."""
    campaign_id = "camp-dynamic-revoke"
    user_id = "user_revoked"
    spicedb = get_spicedb_client()
    client = TestClient(app)

    # 1. Initially granted permission and connects successfully
    _grant("campaign", campaign_id, "view", user_id)
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={user_id}") as ws:
        assert ws.receive_json()["type"] == "connected"

    # 2. Dynamically revoke Zanzibar relationship
    asyncio.run(spicedb.delete_relationship("campaign", campaign_id, "view", "user", user_id))

    # 3. Subsequent connection attempt is rejected with PERMISSION_DENIED and code 4003
    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?user_id={user_id}") as ws:
        err_msg = ws.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "PERMISSION_DENIED"
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4003


def test_spicedb_client_mock_and_grpc_handling():
    """Verify SpiceDBClient handles mock fallback and client instantiation properly."""
    client = SpiceDBClient(use_mock=True)
    assert client.use_mock is True
    assert client._grpc_client is None

    default_client = SpiceDBClient()
    assert default_client._grpc_client is not None

    asyncio.run(default_client.write_relationship("campaign", "c1", "player", "user", "u1"))
    assert asyncio.run(default_client.check_permission("campaign", "c1", "view", "user", "u1"))
    assert not asyncio.run(
        default_client.check_permission("campaign", "c1", "run_session", "user", "u1")
    )
