"""Blackbox tests: gateway audience routes proxy to audience_studio (TASK-0439).

The gateway is called through its public HTTP and WebSocket routes. The owner is a stand-in on a
loopback port (tests/helpers/live_services.py). The stand-in echoes what it receives, so a test
can see the method, path, query, bearer, and body that reached the owner. It answers with the
status that the test selects. The real audience_studio enforces the Zanzibar checks, and its own
suites cover them (tests/test_blackbox_audience_studio*.py). The gateway must pass the owner's
decision on unchanged.

Governed by ADR-0001 (the owner keeps the object checks), ADR-0004 (gateway routing), and
ADR-0015 (b, c): the gateway is thin and forwards the caller's bearer token.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from starlette.websockets import WebSocketDisconnect

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.ws_identity import bearer, ws_subprotocols

DM = "dm-evelyn"
CAMPAIGN = "camp-audience"
POLL = "poll-7"
PROPOSAL = "proposal-3"
ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]


class OwnerStub:
    """A stand-in audience_studio. It echoes each request and answers with `status`."""

    def __init__(self) -> None:
        self.status = 200
        self.calls = 0
        self.app = self._build()

    def _build(self) -> FastAPI:
        app = FastAPI()
        stub = self

        @app.api_route("/api/v1/audience/{rest:path}", methods=ALL_METHODS)
        async def owner_rest(rest: str, request: Request) -> JSONResponse:
            stub.calls += 1
            raw = await request.body()
            if stub.status >= 400:
                return JSONResponse({"error": f"owner answered {stub.status}"}, stub.status)
            return JSONResponse(
                {
                    "method": request.method,
                    "path": request.url.path,
                    "query": dict(request.query_params),
                    "authorization": request.headers.get("authorization"),
                    "body": json.loads(raw) if raw else None,
                },
                status_code=stub.status,
            )

        @app.websocket("/ws/audience/{campaign_id}")
        async def owner_socket(websocket: WebSocket, campaign_id: str) -> None:
            offered = list(websocket.scope.get("subprotocols", []))
            await websocket.accept(subprotocol="runefoble.v1")
            await websocket.send_json(
                {
                    "type": "connected",
                    "campaign_id": campaign_id,
                    "bearer_offered": any(p.startswith("runefoble.bearer.") for p in offered),
                }
            )
            if campaign_id.startswith("camp-denied"):
                await websocket.close(code=4403, reason="no campaign view")
                return
            while True:
                text = await websocket.receive_text()
                await websocket.send_json({"echo": text})

        return app


@pytest.fixture(autouse=True)
def _trust_test_issuer(trusted_ws_issuer) -> Iterator[None]:
    """The gateway verifies bearers against the shared test issuer for every test here."""
    yield


@pytest.fixture
def owner(monkeypatch) -> Iterator[OwnerStub]:
    """Serve the stand-in owner and point the gateway at it before the gateway starts."""
    stub = OwnerStub()
    with serve(stub.app) as url:
        monkeypatch.setenv("RUNEFOBLE_AUDIENCE_STUDIO_URL", url)
        yield stub


@pytest.fixture
def client(owner: OwnerStub) -> Iterator[TestClient]:
    """Enter the gateway lifespan after the owner URL is set, so the registry sees it."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _auth() -> dict[str, str]:
    return bearer(DM)


# --- REST routes: forwarding ----------------------------------------------------------------


def test_create_poll_forwards_the_body_and_bearer_and_relays_the_owner_201(
    client: TestClient, owner: OwnerStub
) -> None:
    owner.status = 201
    body = {"campaign_id": CAMPAIGN, "title": "Storm", "prompt": "Pick", "options": ["a", "b"]}

    res = client.post("/api/v1/audience/polls", json=body, headers=_auth())

    assert res.status_code == 201, res.text
    echoed = res.json()
    assert echoed["method"] == "POST"
    assert echoed["path"] == "/api/v1/audience/polls"
    assert echoed["body"] == body
    assert echoed["authorization"] == _auth()["Authorization"]


def test_read_poll_tallies_forwards_a_get_to_the_owner_poll_path(
    client: TestClient, owner: OwnerStub
) -> None:
    res = client.get(f"/api/v1/audience/polls/{POLL}", headers=_auth())

    assert res.status_code == 200, res.text
    assert res.json()["method"] == "GET"
    assert res.json()["path"] == f"/api/v1/audience/polls/{POLL}"


def test_spectator_vote_forwards_the_json_body_unchanged(
    client: TestClient, owner: OwnerStub
) -> None:
    res = client.post(
        f"/api/v1/audience/polls/{POLL}/votes",
        json={"option_id": "opt-1", "channel": "twitch"},
        headers=_auth(),
    )

    assert res.status_code == 200, res.text
    assert res.json()["path"] == f"/api/v1/audience/polls/{POLL}/votes"
    assert res.json()["body"] == {"option_id": "opt-1", "channel": "twitch"}


def test_close_poll_forwards_a_post_to_the_owner_close_path(
    client: TestClient, owner: OwnerStub
) -> None:
    res = client.post(f"/api/v1/audience/polls/{POLL}/close", headers=_auth())

    assert res.status_code == 200, res.text
    assert res.json()["method"] == "POST"
    assert res.json()["path"] == f"/api/v1/audience/polls/{POLL}/close"
    assert res.json()["body"] is None


def test_list_polls_forwards_the_query_string_to_the_owner(
    client: TestClient, owner: OwnerStub
) -> None:
    res = client.get(f"/api/v1/audience/polls?campaign_id={CAMPAIGN}", headers=_auth())

    assert res.status_code == 200, res.text
    assert res.json()["query"] == {"campaign_id": CAMPAIGN}


def test_list_proposals_forwards_the_campaign_and_status_query(
    client: TestClient, owner: OwnerStub
) -> None:
    res = client.get(
        f"/api/v1/audience/proposals?campaign_id={CAMPAIGN}&status=pending", headers=_auth()
    )

    assert res.status_code == 200, res.text
    assert res.json()["path"] == "/api/v1/audience/proposals"
    assert res.json()["query"] == {"campaign_id": CAMPAIGN, "status": "pending"}


def test_approve_proposal_forwards_to_the_owner_approve_path(
    client: TestClient, owner: OwnerStub
) -> None:
    res = client.post(f"/api/v1/audience/proposals/{PROPOSAL}/approve", headers=_auth())

    assert res.status_code == 200, res.text
    assert res.json()["path"] == f"/api/v1/audience/proposals/{PROPOSAL}/approve"


def test_veto_proposal_forwards_to_the_owner_veto_path(
    client: TestClient, owner: OwnerStub
) -> None:
    res = client.post(f"/api/v1/audience/proposals/{PROPOSAL}/veto", headers=_auth())

    assert res.status_code == 200, res.text
    assert res.json()["path"] == f"/api/v1/audience/proposals/{PROPOSAL}/veto"


# --- REST routes: the owner decides, the gateway relays ------------------------------------


def test_request_without_a_bearer_is_refused_by_the_gateway_before_the_owner(
    client: TestClient, owner: OwnerStub
) -> None:
    res = client.post(f"/api/v1/audience/proposals/{PROPOSAL}/approve")

    assert res.status_code == 401, res.text
    assert owner.calls == 0


@pytest.mark.parametrize("owner_status", [401, 403, 404])
def test_owner_refusal_passes_through_with_its_status_and_body(
    client: TestClient, owner: OwnerStub, owner_status: int
) -> None:
    owner.status = owner_status

    res = client.post(f"/api/v1/audience/proposals/{PROPOSAL}/approve", headers=_auth())

    assert res.status_code == owner_status, res.text
    assert res.json() == {"error": f"owner answered {owner_status}"}


def test_owner_5xx_returns_502_with_the_upstream_name(client: TestClient, owner: OwnerStub) -> None:
    owner.status = 503

    res = client.post(f"/api/v1/audience/polls/{POLL}/close", headers=_auth())

    assert res.status_code == 502, res.text
    assert res.json()["upstream"] == "audience_studio"


def test_owner_unreachable_returns_503_with_the_upstream_name(monkeypatch) -> None:
    monkeypatch.setenv("RUNEFOBLE_AUDIENCE_STUDIO_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        res = client.get(f"/api/v1/audience/polls/{POLL}", headers=_auth())

    assert res.status_code == 503, res.text
    assert res.json()["upstream"] == "audience_studio"


def test_unset_owner_url_returns_503_and_no_substitute_body(monkeypatch) -> None:
    monkeypatch.setenv("RUNEFOBLE_AUDIENCE_STUDIO_URL", "")
    with TestClient(gateway_app) as client:
        res = client.get(f"/api/v1/audience/polls/{POLL}", headers=_auth())

    assert res.status_code == 503, res.text
    assert res.json()["upstream"] == "audience_studio"


# --- WebSocket route ------------------------------------------------------------------------


def test_websocket_relays_frames_and_offers_the_bearer_to_the_owner(
    client: TestClient, owner: OwnerStub
) -> None:
    with client.websocket_connect(
        f"/ws/audience/{CAMPAIGN}", subprotocols=ws_subprotocols(DM)
    ) as ws:
        connected = ws.receive_json()
        assert connected["type"] == "connected"
        assert connected["campaign_id"] == CAMPAIGN
        assert connected["bearer_offered"] is True

        ws.send_text("cast_vote")
        assert ws.receive_json() == {"echo": "cast_vote"}


def test_websocket_passes_the_owner_close_code_to_the_client(
    client: TestClient, owner: OwnerStub
) -> None:
    with client.websocket_connect(
        "/ws/audience/camp-denied-1", subprotocols=ws_subprotocols("stranger-mallory")
    ) as ws:
        assert ws.receive_json()["type"] == "connected"
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()

    assert closed.value.code == 4403


def test_websocket_without_a_bearer_is_closed_before_the_owner_is_reached(
    client: TestClient, owner: OwnerStub
) -> None:
    with (
        pytest.raises(WebSocketDisconnect) as refused,
        client.websocket_connect(f"/ws/audience/{CAMPAIGN}", subprotocols=["runefoble.v1"]),
    ):
        pass

    assert refused.value.code == 1008
    assert owner.calls == 0


def test_websocket_owner_unreachable_closes_with_try_again_later(monkeypatch) -> None:
    monkeypatch.setenv("RUNEFOBLE_AUDIENCE_STUDIO_URL", closed_port_url())
    with (
        TestClient(gateway_app) as client,
        client.websocket_connect(
            f"/ws/audience/{CAMPAIGN}", subprotocols=ws_subprotocols(DM)
        ) as ws,
        pytest.raises(WebSocketDisconnect) as closed,
    ):
        ws.receive_json()

    assert closed.value.code == 1013
