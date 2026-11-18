"""Blackbox tests: gateway voice room and stream routes proxy to voice_agent (TASK-0593).

The gateway is called through its public HTTP routes and WebSocket. voice_agent runs as a live
loopback upstream (tests/helpers/live_services.py). Room state is written through the public
voice signaling socket. Governed by ADR-0007 and ADR-0015 (b, c).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.voice_identity import voice_auth_headers
from tests.helpers.ws_identity import ws_subprotocols


@pytest.fixture
def owner_gateway(voice_agent_upstream: str) -> Iterator[TestClient]:
    """Gateway client wired to a live voice_agent. The URL is set before the lifespan runs."""
    with TestClient(gateway_app) as client:
        yield client


def test_room_state_written_on_the_voice_socket_is_read_through_the_gateway(
    owner_gateway: TestClient, table_for
) -> None:
    user_id = "user_bard"
    _, session_id = table_for("dm_dora", {user_id: "player"})

    with owner_gateway.websocket_connect(
        f"/ws/voice/{session_id}?peer_id=peer_bard", subprotocols=ws_subprotocols(user_id)
    ) as ws:
        ws.receive_json()
        ws.receive_json()
        res = owner_gateway.get(
            f"/api/v1/voice/rooms/{session_id}", headers=voice_auth_headers(user_id)
        )

    assert res.status_code == 200, res.text
    peers = [p["peer_id"] for p in res.json()["participants"]]
    assert "peer_bard" in peers


def test_missing_bearer_is_refused_by_the_owner_and_passed_through(
    owner_gateway: TestClient,
) -> None:
    res = owner_gateway.get("/api/v1/voice/rooms/sess-no-token")
    assert res.status_code == 401
    assert res.json()["detail"]


def test_kick_without_bearer_is_passed_through_as_401(owner_gateway: TestClient) -> None:
    res = owner_gateway.post(
        "/api/v1/voice/rooms/sess-no-token/kick",
        json={"peer_id": "peer-x", "reason": "mic_spam"},
    )
    assert res.status_code == 401


def test_owner_unreachable_returns_503_with_upstream_name(
    monkeypatch, trusted_voice_issuer
) -> None:
    monkeypatch.setenv("RUNEFOBLE_VOICE_AGENT_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        res = client.get("/api/v1/voice/rooms/sess-down", headers=voice_auth_headers("user_dm"))
    assert res.status_code == 503
    assert res.json()["upstream"] == "voice_agent"


def test_owner_5xx_returns_502_with_upstream_name(monkeypatch, trusted_voice_issuer) -> None:
    with serve(unavailable_app(500)) as url:
        monkeypatch.setenv("RUNEFOBLE_VOICE_AGENT_URL", url)
        with TestClient(gateway_app) as client:
            res = client.get(
                "/api/v1/voice/rooms/sess-broken", headers=voice_auth_headers("user_dm")
            )
    assert res.status_code == 502
    assert res.json()["upstream"] == "voice_agent"


def test_stream_quality_query_reaches_the_owner_with_peer_filter(
    owner_gateway: TestClient, table_for
) -> None:
    user_id = "user_lute"
    _, session_id = table_for("dm_dora", {user_id: "player"})

    res = owner_gateway.get(
        f"/api/v1/voice/streams/{session_id}/quality?peer_id=peer_lute",
        headers=voice_auth_headers(user_id),
    )
    # A player lacks session.control. voice_agent refuses, and the gateway passes 403 through.
    assert res.status_code == 403, res.text
