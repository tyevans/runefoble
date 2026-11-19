"""Blackbox TDD Suite for Zitadel WebSocket Token Verification and Handshake Authorization.

Governed by:
- ADR-0001: SpiceDB Zanzibar Object Authorization
- ADR-0015 (c): WebSocket clients send the token in Sec-WebSocket-Protocol only
- TASK-0034: Zitadel Production OIDC/JWKS Token Verification Middleware
- TASK-0520: Verified principal and bearer subprotocol contract
- TASK-0522: Gateway WebSocket routes authenticate before accept

A refused handshake raises WebSocketDisconnect before any frame is delivered.
An admitted handshake that lacks SpiceDB permission gets a PERMISSION_DENIED frame and close 4403.
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.mock import MockSpiceDBClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.signing_test_issuer import SigningTestIssuer
from tests.helpers.ws_identity import SIGNING_ISSUER, ws_subprotocols

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

RUNEFOBLE_PROTOCOL = "runefoble.v1"


@pytest.fixture
def spicedb() -> MockSpiceDBClient:
    client = get_spicedb_client()
    yield client


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _grant_view(spicedb: MockSpiceDBClient, campaign_id: str, user_id: str) -> None:
    asyncio.run(spicedb.write_relationship("campaign", campaign_id, "spectator", "user", user_id))


def test_valid_bearer_subprotocol_connects(client: TestClient, spicedb: MockSpiceDBClient) -> None:
    """Frontdoor test: a valid token in the bearer subprotocol connects and is accepted."""
    campaign_id = "camp-ws-valid-01"
    user_id = "ws_user_kyra"
    _grant_view(spicedb, campaign_id, user_id)

    with client.websocket_connect(
        f"/ws/campaigns/{campaign_id}", subprotocols=ws_subprotocols(user_id)
    ) as ws:
        assert ws.accepted_subprotocol == RUNEFOBLE_PROTOCOL
        msg = ws.receive_json()
        assert msg["type"] == "connected"
        assert msg["campaign_id"] == campaign_id
        assert msg["user_id"] == user_id


def test_valid_token_without_permission_gets_4403(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Frontdoor test: a verified stranger is admitted, then refused by SpiceDB with 4403."""
    campaign_id = "camp-ws-unauthorized-01"

    with client.websocket_connect(
        f"/ws/campaigns/{campaign_id}", subprotocols=ws_subprotocols("ws_unauthorized_stranger")
    ) as ws:
        err_msg = ws.receive_json()
        assert err_msg["type"] == "error"
        assert err_msg["code"] == "PERMISSION_DENIED"
        assert "insufficient permissions" in err_msg["message"]

        with pytest.raises(WebSocketDisconnect) as exc_info:
            ws.receive_json()
        assert exc_info.value.code == 4403


def test_token_in_query_string_is_refused(client: TestClient, spicedb: MockSpiceDBClient) -> None:
    """Frontdoor test: a token in the URL query string never admits the handshake."""
    campaign_id = "camp-ws-query-01"
    user_id = "ws_user_query"
    _grant_view(spicedb, campaign_id, user_id)
    token = SIGNING_ISSUER.mint(user_id)

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/ws/campaigns/{campaign_id}?token={token}"),
    ):
        pass


def test_authorization_header_alone_is_refused(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Frontdoor test: browsers cannot send Authorization on WebSockets, so the header is ignored."""
    campaign_id = "camp-ws-header-01"
    user_id = "ws_user_header"
    _grant_view(spicedb, campaign_id, user_id)
    token = SIGNING_ISSUER.mint(user_id)

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/ws/campaigns/{campaign_id}", headers={"Authorization": f"Bearer {token}"}
        ),
    ):
        pass


def test_legacy_prefix_without_dot_is_refused(
    client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """Frontdoor test: only the runefoble.bearer.<jwt> form is accepted, not bearer.<jwt>."""
    campaign_id = "camp-ws-legacy-01"
    user_id = "ws_user_legacy"
    _grant_view(spicedb, campaign_id, user_id)
    token = SIGNING_ISSUER.mint(user_id)

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            f"/ws/campaigns/{campaign_id}", subprotocols=[RUNEFOBLE_PROTOCOL, f"bearer.{token}"]
        ),
    ):
        pass


def test_forged_signature_is_refused(client: TestClient) -> None:
    """Frontdoor test: a token signed by an untrusted key never admits the handshake."""
    attacker = SigningTestIssuer(issuer=SIGNING_ISSUER.issuer, kid=SIGNING_ISSUER.kid)
    forged = attacker.mint("ws_attacker")

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            "/ws/campaigns/camp-ws", subprotocols=[RUNEFOBLE_PROTOCOL, f"runefoble.bearer.{forged}"]
        ),
    ):
        pass


def test_expired_token_is_refused(client: TestClient) -> None:
    """Frontdoor test: an expired token never admits the handshake."""
    expired = SIGNING_ISSUER.mint("ws_user", expires_in=-60)

    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            "/ws/campaigns/camp-ws",
            subprotocols=[RUNEFOBLE_PROTOCOL, f"runefoble.bearer.{expired}"],
        ),
    ):
        pass


def test_missing_token_is_refused(client: TestClient) -> None:
    """Frontdoor test: a handshake with no bearer subprotocol is refused."""
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws/campaigns/camp-ws"):
        pass
