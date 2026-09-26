"""Blackbox TDD Suite for Zitadel WebSocket Token Verification and Handshake Authorization.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0009: Continuous Backlog Refinement and Technical Debt Management
- TASK-0034: Zitadel Production OIDC/JWKS Token Verification Middleware
- TASK-0079: Zitadel OIDC Token Verification Blackbox Test Suite Modular Decomposition
"""

import pytest
from starlette.testclient import WebSocketDenialResponse
from starlette.websockets import WebSocketDisconnect

from tests.helpers.zitadel_auth import create_signed_token


@pytest.mark.asyncio
async def test_websocket_valid_signed_token_in_query_succeeds(auth_environment):
    """Frontdoor test: Valid signed token in WebSocket query parameter connects successfully."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]
    spicedb = auth_environment["spicedb"]

    campaign_id = "camp-ws-valid-01"
    user_id = "ws_user_kyra"

    await spicedb.write_relationship("campaign", campaign_id, "view", "user", user_id)

    token = create_signed_token(valid_key, sub=user_id, kid=kid)

    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?token={token}") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["campaign_id"] == campaign_id
        assert msg["user_id"] == user_id


@pytest.mark.asyncio
async def test_websocket_valid_signed_token_in_header_succeeds(auth_environment):
    """Frontdoor test: Valid signed token in WebSocket Authorization header connects successfully."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]
    spicedb = auth_environment["spicedb"]

    campaign_id = "camp-ws-valid-02"
    user_id = "ws_user_merisiel"

    await spicedb.write_relationship("campaign", campaign_id, "view", "user", user_id)

    token = create_signed_token(valid_key, sub=user_id, kid=kid)

    with client.websocket_connect(
        f"/ws/campaigns/{campaign_id}",
        headers={"Authorization": f"Bearer {token}"},
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["user_id"] == user_id


@pytest.mark.asyncio
async def test_websocket_valid_signed_token_in_subprotocol_succeeds(auth_environment):
    """Frontdoor test: Valid signed token in Sec-WebSocket-Protocol header connects successfully."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]
    spicedb = auth_environment["spicedb"]

    campaign_id = "camp-ws-subproto-01"
    user_id = "ws_user_seoni"

    await spicedb.write_relationship("campaign", campaign_id, "view", "user", user_id)

    token = create_signed_token(valid_key, sub=user_id, kid=kid)

    with client.websocket_connect(
        f"/ws/campaigns/{campaign_id}",
        subprotocols=[f"bearer.{token}"],
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["campaign_id"] == campaign_id
        assert msg["user_id"] == user_id


def test_websocket_unauthorized_user_rejected_4003(auth_environment):
    """Frontdoor test: Valid token for user lacking SpiceDB Zanzibar permissions receives 4003 close frame."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]

    campaign_id = "camp-ws-unauthorized-01"
    user_id = "ws_unauthorized_stranger"

    token = create_signed_token(valid_key, sub=user_id, kid=kid)

    with client.websocket_connect(f"/ws/campaigns/{campaign_id}?token={token}") as ws:
        err_msg = ws.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "PERMISSION_DENIED"
        assert "insufficient permissions" in err_msg["message"]

        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4003


def test_websocket_forged_signature_rejected_401(auth_environment):
    """Frontdoor test: Forged token in WebSocket connection is rejected with 401 Unauthorized."""
    client = auth_environment["client"]
    attacker_key = auth_environment["attacker_key"]
    kid = auth_environment["kid"]

    forged_token = create_signed_token(attacker_key, sub="ws_attacker", kid=kid)

    with (
        pytest.raises(WebSocketDenialResponse) as exc_info,
        client.websocket_connect(f"/ws/campaigns/camp-ws?token={forged_token}"),
    ):
        pass

    assert exc_info.value.status_code == 401


def test_websocket_expired_token_rejected_401(auth_environment):
    """Frontdoor test: Expired token in WebSocket connection is rejected with 401 Unauthorized."""
    client = auth_environment["client"]
    valid_key = auth_environment["valid_key"]
    kid = auth_environment["kid"]

    expired_token = create_signed_token(valid_key, sub="ws_user", exp_offset=-60, kid=kid)

    with (
        pytest.raises(WebSocketDenialResponse) as exc_info,
        client.websocket_connect(f"/ws/campaigns/camp-ws?token={expired_token}"),
    ):
        pass

    assert exc_info.value.status_code == 401


def test_websocket_missing_token_rejected_in_production(auth_environment):
    """Frontdoor test: Missing token in WebSocket handshake in production mode is rejected with 401."""
    client = auth_environment["client"]

    with (
        pytest.raises(WebSocketDenialResponse) as exc_info,
        client.websocket_connect("/ws/campaigns/camp-ws?user_id=spoofed_user"),
    ):
        pass

    assert exc_info.value.status_code == 401
