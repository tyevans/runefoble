"""Blackbox tests: gateway settlement REST and minigame sockets reach game_session (TASK-0592).

The gateway is called through its public HTTP and WebSocket routes. The owner runs as a live
loopback upstream. Settlement state must live in game_session: a settlement founded through the
gateway is read back from the owner. Socket frames pass through the gateway unchanged, the bearer
subprotocol reaches the owner, and owner close codes reach the client.
Governed by ADR-0007 (owner holds state), ADR-0015 (b) thin gateway, (c) verified bearer, and
Hard Invariant 7 (blackbox setup through frontdoors).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_auth.mock import MockSpiceDBClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.minigame_tables import open_minigame_table
from tests.helpers.ws_identity import ws_subprotocols

RUNEFOBLE_PROTOCOL = "runefoble.v1"


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.fixture
def gateway_client(game_session_upstream: str) -> Iterator[TestClient]:
    """Enter the gateway lifespan after the owner URL is set, so the relay sees it."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def owner(trusted_ws_issuer) -> dict[str, str]:
    return _auth(trusted_ws_issuer, "dm-evelyn")


@pytest.fixture
def campaign_id(gateway_client: TestClient, owner: dict[str, str]) -> str:
    """A campaign created through the gateway. The caller becomes its owner."""
    res = gateway_client.post("/api/v1/campaigns", json={"title": "Tomb"}, headers=owner)
    assert res.status_code == 201, res.text
    return res.json()["id"]


# --- REST ---------------------------------------------------------------------------------------


def test_settlement_founded_through_gateway_is_read_from_the_owner(
    gateway_client: TestClient, game_session_upstream: str, owner, campaign_id: str
) -> None:
    founded = gateway_client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Haven", "scale": "village"},
        headers=owner,
    )
    assert founded.status_code == 201, founded.text
    settlement_id = founded.json()["settlement_id"]

    owner_view = httpx.get(
        f"{game_session_upstream}/api/v1/campaigns/{campaign_id}/settlements",
        headers=owner,
        timeout=5.0,
    )
    assert owner_view.status_code == 200, owner_view.text
    assert settlement_id in [s["settlement_id"] for s in owner_view.json()]


def test_settlement_read_through_gateway_matches_the_owner(
    gateway_client: TestClient, game_session_upstream: str, owner, campaign_id: str
) -> None:
    sid = gateway_client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Haven", "scale": "village"},
        headers=owner,
    ).json()["settlement_id"]

    via_gateway = gateway_client.get(
        f"/api/v1/campaigns/{campaign_id}/settlements/{sid}", headers=owner
    )
    via_owner = httpx.get(
        f"{game_session_upstream}/api/v1/campaigns/{campaign_id}/settlements/{sid}",
        headers=owner,
        timeout=5.0,
    )
    assert via_gateway.status_code == via_owner.status_code == 200
    assert via_gateway.json() == via_owner.json()


def test_settlement_route_without_token_is_refused_before_any_upstream_call(
    gateway_client: TestClient, campaign_id: str
) -> None:
    res = gateway_client.post(
        f"/api/v1/campaigns/{campaign_id}/settlements",
        json={"name": "Haven", "scale": "village"},
    )
    assert res.status_code == 401


def test_owner_client_error_passes_through_unchanged(
    gateway_client: TestClient, game_session_upstream: str, owner
) -> None:
    missing = f"missing-{uuid4().hex[:6]}"
    via_gateway = gateway_client.get(f"/api/v1/establishments/{missing}", headers=owner)
    via_owner = httpx.get(
        f"{game_session_upstream}/api/v1/establishments/{missing}", headers=owner, timeout=5.0
    )
    assert via_gateway.status_code == via_owner.status_code
    assert via_gateway.status_code >= 400 and via_gateway.status_code < 500
    assert via_gateway.json() == via_owner.json()


def test_owner_unreachable_returns_503_for_settlement_routes(
    campaign_id: str, owner, monkeypatch
) -> None:
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        res = client.get(f"/api/v1/campaigns/{campaign_id}/settlements", headers=owner)
    assert res.status_code == 503
    assert res.json()["upstream"] == "game_session"


# --- WebSocket relay against game_session -------------------------------------------------------


@pytest.fixture
def open_table(spicedb: MockSpiceDBClient, game_session_upstream: str) -> str:
    """Open a darts table through the owner's public route. The tester is a patron of est-default."""
    asyncio.run(
        spicedb.write_relationship(
            "establishment", "est-default", "patron", "user", "minigame-tester"
        )
    )
    table_id = f"table-relay-{uuid4().hex[:6]}"
    open_minigame_table(table_id, game_type="darts")
    return table_id


@pytest.mark.parametrize(
    "path_template",
    ["/ws/minigames/{table_id}", "/ws/establishments/est-default/tables/{table_id}"],
)
def test_frame_sent_through_gateway_reaches_owner_and_comes_back(
    gateway_client: TestClient, open_table: str, path_template: str
) -> None:
    path = path_template.format(table_id=open_table)
    with gateway_client.websocket_connect(
        path, subprotocols=ws_subprotocols("minigame-tester")
    ) as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected" and connected["table_id"] == open_table
        ws.send_json({"action": "relay_probe", "n": 7})
        assert ws.receive_json() == {"action": "relay_probe", "n": 7}


# --- WebSocket relay against a stand-in owner ---------------------------------------------------


def _stand_in_owner() -> FastAPI:
    """An owner that reports the subprotocols it received, then obeys the table id it was given."""
    app = FastAPI()

    @app.websocket("/ws/minigames/{table_id}")
    async def owner_socket(websocket: WebSocket, table_id: str) -> None:
        if table_id == "refuse":
            await websocket.close(code=1008)
            return
        await websocket.accept(subprotocol=RUNEFOBLE_PROTOCOL)
        offered = list(websocket.scope.get("subprotocols", []))
        await websocket.send_json({"type": "hello", "subprotocols": offered})
        if table_id == "close-4403":
            await websocket.close(code=4403, reason="session.observe required")
            return
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            if message.get("text") is not None:
                await websocket.send_text(message["text"])
            elif message.get("bytes") is not None:
                await websocket.send_bytes(message["bytes"])

    return app


@pytest.fixture
def stand_in_owner(monkeypatch, trusted_ws_issuer) -> Iterator[str]:
    with serve(_stand_in_owner()) as url:
        monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", url)
        yield url


@pytest.fixture
def stand_in_gateway(stand_in_owner: str) -> Iterator[TestClient]:
    with TestClient(gateway_app) as client:
        yield client


def test_bearer_subprotocol_reaches_owner_and_text_and_binary_frames_round_trip(
    stand_in_gateway: TestClient, trusted_ws_issuer
) -> None:
    subprotocols = ws_subprotocols("minigame-tester")
    with stand_in_gateway.websocket_connect("/ws/minigames/echo", subprotocols=subprotocols) as ws:
        assert ws.accepted_subprotocol == RUNEFOBLE_PROTOCOL
        hello = ws.receive_json()
        assert hello["subprotocols"] == subprotocols
        ws.send_text("ping")
        assert ws.receive_text() == "ping"
        ws.send_bytes(b"\x00\x01\x02")
        assert ws.receive_bytes() == b"\x00\x01\x02"


def test_owner_close_code_4403_reaches_the_client(stand_in_gateway: TestClient) -> None:
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        stand_in_gateway.websocket_connect(
            "/ws/minigames/close-4403", subprotocols=ws_subprotocols("minigame-tester")
        ) as ws,
    ):
        ws.receive_json()
        ws.receive_json()
    assert closed.value.code == 4403


def test_owner_refusal_before_accept_reaches_the_client_as_4403(
    stand_in_gateway: TestClient,
) -> None:
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        stand_in_gateway.websocket_connect(
            "/ws/minigames/refuse", subprotocols=ws_subprotocols("minigame-tester")
        ) as ws,
    ):
        ws.receive_json()
    assert closed.value.code == 4403


def test_unreachable_owner_closes_the_client_socket_with_1013(
    monkeypatch, trusted_ws_issuer
) -> None:
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())
    with (
        TestClient(gateway_app) as client,
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(
            "/ws/minigames/echo", subprotocols=ws_subprotocols("minigame-tester")
        ) as ws,
    ):
        ws.receive_json()
    assert closed.value.code == 1013


def test_socket_without_token_is_refused_before_the_owner_is_called(
    stand_in_gateway: TestClient,
) -> None:
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        stand_in_gateway.websocket_connect("/ws/minigames/echo"),
    ):
        pass
    assert closed.value.code == 1008
