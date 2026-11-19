"""Blackbox frontdoor tests: every gateway WebSocket route admits callers through one helper.

Governed by ADR-0001, ADR-0015 (c), and Hard Invariant 7. The close codes follow
`docs/reference/ports-and-endpoints.md`: 1008 for a missing or invalid token, 4403 for an
authorization refusal, and 1011 when SpiceDB cannot answer. Setup runs over HTTP only.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.errors import AuthzUnavailableError
from starlette.websockets import WebSocketDisconnect

from tests.helpers.spicedb_factory import shared_spicedb_client
from tests.helpers.ws_identity import ws_subprotocols

POLICY_VIOLATION = 1008
FORBIDDEN = 4403
AUTHORIZATION_UNAVAILABLE = 1011

# (route, a member who holds session.observe, the first frame that member receives)
OBSERVE_ROUTES = [
    ("/ws/session/{sid}", "player_pip", "connected"),
    ("/ws/voice/{sid}", "player_pip", "connected"),
    ("/ws/mobile-companion/{sid}", "player_pip", "mobile_companion_connected"),
    ("/ws/overlay/{sid}", "spectator_sol", "overlay_connected"),
    ("/ws/spectator/{sid}", "spectator_sol", "overlay_connected"),
]
STRANGER = "stranger_eve"


@pytest.fixture
def gateway(board_gateway: TestClient) -> TestClient:
    return board_gateway


@pytest.fixture
def table(board_table) -> tuple[str, str]:
    """A campaign (campaign id, session id) with a player and a spectator. Stranger is not a member."""
    return board_table(
        "dm_dora",
        {"player_pip": "player", "spectator_sol": "spectator"},
    )


@pytest.mark.parametrize(("route", "member", "first_frame"), OBSERVE_ROUTES)
def test_session_socket_without_a_bearer_is_closed_with_1008(
    gateway: TestClient, table: tuple[str, str], route: str, member: str, first_frame: str
) -> None:
    _, session_id = table

    with (
        pytest.raises(WebSocketDisconnect) as closed,
        gateway.websocket_connect(route.format(sid=session_id)),
    ):
        pass

    assert closed.value.code == POLICY_VIOLATION


@pytest.mark.parametrize(("route", "member", "first_frame"), OBSERVE_ROUTES)
def test_session_socket_refuses_a_stranger_with_4403(
    gateway: TestClient, table: tuple[str, str], route: str, member: str, first_frame: str
) -> None:
    _, session_id = table

    with (
        pytest.raises(WebSocketDisconnect) as refused,
        gateway.websocket_connect(
            route.format(sid=session_id), subprotocols=ws_subprotocols(STRANGER)
        ) as ws,
    ):
        ws.receive_json()

    assert refused.value.code == FORBIDDEN


@pytest.mark.parametrize(("route", "member", "first_frame"), OBSERVE_ROUTES)
def test_session_socket_admits_a_member(
    gateway: TestClient, table: tuple[str, str], route: str, member: str, first_frame: str
) -> None:
    _, session_id = table

    with gateway.websocket_connect(
        route.format(sid=session_id), subprotocols=ws_subprotocols(member)
    ) as ws:
        assert ws.receive_json()["type"] == first_frame


def test_campaign_socket_without_a_bearer_is_closed_with_1008(
    gateway: TestClient, table: tuple[str, str]
) -> None:
    campaign_id, _ = table

    with (
        pytest.raises(WebSocketDisconnect) as closed,
        gateway.websocket_connect(f"/ws/campaigns/{campaign_id}"),
    ):
        pass

    assert closed.value.code == POLICY_VIOLATION


def test_campaign_socket_refuses_a_stranger_with_a_permission_frame_then_4403(
    gateway: TestClient, table: tuple[str, str]
) -> None:
    campaign_id, _ = table

    with (
        pytest.raises(WebSocketDisconnect) as refused,
        gateway.websocket_connect(
            f"/ws/campaigns/{campaign_id}", subprotocols=ws_subprotocols(STRANGER)
        ) as ws,
    ):
        frame = ws.receive_json()
        assert frame["type"] == "error"
        assert frame["code"] == "PERMISSION_DENIED"
        ws.receive_json()

    assert refused.value.code == FORBIDDEN


def test_campaign_socket_admits_a_member(gateway: TestClient, table: tuple[str, str]) -> None:
    campaign_id, _ = table

    with gateway.websocket_connect(
        f"/ws/campaigns/{campaign_id}", subprotocols=ws_subprotocols("player_pip")
    ) as ws:
        assert ws.receive_json()["type"] == "connected"


class _OutageSpiceDB:
    """Stands in for SpiceDB at the process boundary. Every check fails to reach it."""

    async def check_permission(self, *args, **kwargs) -> bool:
        raise AuthzUnavailableError("UNAVAILABLE: connection refused to spicedb:50051")


def test_socket_closes_with_1011_when_spicedb_is_unavailable_not_4403(
    gateway: TestClient, table: tuple[str, str]
) -> None:
    _, session_id = table

    with (
        shared_spicedb_client(_OutageSpiceDB()),
        pytest.raises(WebSocketDisconnect) as closed,
        gateway.websocket_connect(
            f"/ws/session/{session_id}", subprotocols=ws_subprotocols("player_pip")
        ) as ws,
    ):
        ws.receive_json()

    assert closed.value.code == AUTHORIZATION_UNAVAILABLE
