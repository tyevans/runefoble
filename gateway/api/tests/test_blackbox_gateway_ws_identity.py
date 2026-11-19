"""Blackbox tests: every gateway WebSocket route authenticates before accept.

Governed by:
- TASK-0522: Gateway WebSocket and Signaling Connections Authenticate Before Accept
- TASK-0520: Verified principal and bearer subprotocol contract
- ADR-0015 (c): WebSocket clients send the token in Sec-WebSocket-Protocol, never in the query string

Setup goes through the public verifier boundary only: a SigningTestIssuer mints
RS256 tokens and the gateway trusts that issuer. No route state is written here.
"""

from __future__ import annotations

from collections.abc import Iterator

import jwt
import pytest
from fastapi.testclient import TestClient
from game_session.settlement.auth.tokens import (
    get_zitadel_auth_service as get_session_auth,
)
from game_session.settlement.auth.tokens import (
    set_zitadel_auth_service as set_session_auth,
)
from gateway_api.auth import (
    get_zitadel_auth_service,
    set_zitadel_auth_service,
)
from gateway_api.main import app
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from starlette.websockets import WebSocketDisconnect

from tests.helpers.module_state import SeamRestorer

RUNEFOBLE_PROTOCOL = "runefoble.v1"

# The eight route groups named in TASK-0522 step 2.
ROUTE_GROUPS = [
    pytest.param("/ws/campaigns/camp-ws-identity", id="campaigns"),
    pytest.param("/ws/session/sess-ws-identity", id="session"),
    pytest.param("/ws/voice/sess-ws-identity", id="voice-signaling"),
    pytest.param("/ws/mobile-companion/sess-ws-identity", id="mobile-companion"),
    pytest.param(
        "/ws/establishments/est-ws-identity/tables/table-ws-identity", id="establishment-table"
    ),
    pytest.param("/ws/minigames/table-ws-identity", id="standalone-minigame"),
    pytest.param("/ws/overlay/sess-ws-identity", id="overlay"),
    pytest.param("/ws/spectator/sess-ws-identity", id="spectator"),
]


# The session route also needs `session.observe`. Its accepted path is covered in
# tests/test_blackbox_campaign_and_lobby/test_session_ws_scope.py with a real session.
# The two minigame routes are relayed to game_session, so their accept path needs a live owner.
# The overlay and spectator routes need `session.observe`. Their accepted path is covered in
# tests/test_blackbox_gateway_realtime_authz.py with a real campaign session.
# tests/test_blackbox_gateway_settlement_proxy.py covers them with one.
ACCEPTING_ROUTES = [
    route
    for route in ROUTE_GROUPS
    if route.id
    not in (
        "session",
        "voice-signaling",
        "mobile-companion",
        "establishment-table",
        "standalone-minigame",
        "overlay-alias",
        "overlay",
        "spectator",
    )
]


@pytest.fixture
def issuer() -> SigningTestIssuer:
    return SigningTestIssuer()


@pytest.fixture
def client(issuer: SigningTestIssuer, seam_restorer: SeamRestorer) -> Iterator[TestClient]:
    """Trust the test issuer in both the gateway and the game_session verifiers."""
    seam_restorer.replace(get_zitadel_auth_service, set_zitadel_auth_service, issuer.verifier())
    seam_restorer.replace(get_session_auth, set_session_auth, issuer.verifier())
    yield TestClient(app)


def _bearer(token: str) -> list[str]:
    return [RUNEFOBLE_PROTOCOL, f"runefoble.bearer.{token}"]


@pytest.mark.parametrize("path", ROUTE_GROUPS)
def test_no_token_denies_handshake(client: TestClient, path: str) -> None:
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(path):
        pass


@pytest.mark.parametrize("path", ROUTE_GROUPS)
def test_garbage_token_denies_handshake(client: TestClient, path: str) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(path, subprotocols=_bearer("not-a-jwt")),
    ):
        pass


@pytest.mark.parametrize("path", ROUTE_GROUPS)
def test_forged_hs256_token_denies_handshake(
    client: TestClient, issuer: SigningTestIssuer, path: str
) -> None:
    forged = jwt.encode(
        {"sub": "user-forged", "iss": issuer.issuer, "aud": issuer.audience, "exp": 4102444800},
        "attacker-secret-key-with-more-than-32-bytes",
        algorithm="HS256",
    )
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(path, subprotocols=_bearer(forged)),
    ):
        pass


@pytest.mark.parametrize("path", ROUTE_GROUPS)
def test_query_string_identity_denies_handshake(client: TestClient, path: str) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"{path}?user_id=someone&token=anything"),
    ):
        pass


@pytest.mark.parametrize("path", ROUTE_GROUPS)
def test_x_user_id_header_denies_handshake(client: TestClient, path: str) -> None:
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(path, headers={"x-user-id": "someone"}),
    ):
        pass


@pytest.mark.parametrize("path", ACCEPTING_ROUTES)
def test_valid_bearer_subprotocol_accepts_handshake(
    client: TestClient, issuer: SigningTestIssuer, path: str
) -> None:
    token = issuer.mint("user-ws-identity")
    with client.websocket_connect(path, subprotocols=_bearer(token)) as ws:
        assert ws.accepted_subprotocol == RUNEFOBLE_PROTOCOL


def test_expired_token_denies_handshake(client: TestClient, issuer: SigningTestIssuer) -> None:
    expired = issuer.mint("user-ws-identity", expires_in=-60)
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/ws/session/sess-ws-identity", subprotocols=_bearer(expired)),
    ):
        pass


def test_gateway_verifier_is_the_one_used(client: TestClient) -> None:
    """A token from an untrusted issuer is refused even with a valid RS256 signature."""
    other = SigningTestIssuer(issuer="http://other-zitadel.test", kid="other-key")
    foreign = other.mint("user-ws-identity")
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/ws/session/sess-ws-identity", subprotocols=_bearer(foreign)),
    ):
        pass
