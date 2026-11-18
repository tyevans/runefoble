"""Blackbox frontdoor tests: gateway lore write routes proxy to campaign_lore (TASK-0695).

The gateway is called through its public HTTP routes. campaign_lore is a real HTTP stand-in on
a loopback port (ADR-0014). The stand-in verifies the forwarded bearer token with the test
issuer that the gateway trusts, and records each body it receives. Failures are real: a closed
port, a 503 owner, and a 403 owner each reach the caller as an error. No canned pin or entry
is returned.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_auth.principal import authenticate_authorization

from tests.helpers.live_services import closed_port_url, serve, unavailable_app

PIN_BODY = {
    "title": "Star-Eater Gate",
    "coordinates": {"x": 320.0, "y": 180.0},
    "layer": "continental",
}
ENTRY_BODY = {
    "title": "The Star-Eater Relic",
    "content": "A relic that hums near the gate.",
    "privacy": "party_shared",
}


def _owner_stand_in(
    received: list[dict[str, Any]], verifier: Any, reply: dict[str, int]
) -> FastAPI:
    """Return a campaign_lore stand-in that accepts POSTs and records them."""
    app = FastAPI()

    @app.post("/{path:path}")
    async def _write(path: str, request: Request) -> JSONResponse:
        principal = authenticate_authorization(verifier, request.headers.get("authorization"))
        body = await request.json()
        received.append(
            {
                "path": request.url.path,
                "authorization": request.headers.get("authorization"),
                "x_user_id": request.headers.get("x-user-id"),
                "subject": principal.user_id,
                "body": body,
            }
        )
        if reply["status"] >= 400:
            return JSONResponse(status_code=reply["status"], content={"detail": "owner refused"})
        if path.endswith("/atlas/pins"):
            return JSONResponse(status_code=201, content={"pin_id": "pin-owner", **body})
        return JSONResponse(status_code=201, content={"entry_id": "entry-owner", **body})

    return app


@pytest.fixture
def lore_reply() -> dict[str, int]:
    return {"status": 201}


@pytest.fixture
def lore_received(monkeypatch, trusted_ws_issuer, lore_reply) -> Iterator[list[dict[str, Any]]]:
    """Serve the campaign_lore stand-in and point the gateway at it."""
    received: list[dict[str, Any]] = []
    with serve(_owner_stand_in(received, trusted_ws_issuer.verifier(), lore_reply)) as lore_url:
        monkeypatch.setenv("CAMPAIGN_LORE_URL", lore_url)
        yield received


@pytest.fixture
def client(lore_received, game_session_upstream) -> Iterator[TestClient]:
    """Run the gateway lifespan after the upstream URLs are set, so clients see them."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def owner(client: TestClient, trusted_ws_issuer) -> tuple[str, dict[str, str]]:
    """Create a campaign through the public frontdoor. Return its id and the owner's headers."""
    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('dm_valeros')}"}
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Tomb of the Star-Eater", "setting": "Astral Void", "system": "5e"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"], headers


def test_create_pin_forwards_body_and_bearer_and_returns_owner_pin(
    client: TestClient, owner, lore_received
) -> None:
    campaign_id, headers = owner
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/atlas/pins",
        json=PIN_BODY,
        headers={**headers, "X-User-Id": "spoofed-user"},
    )

    assert res.status_code == 201, res.text
    assert res.json()["pin_id"] == "pin-owner"
    assert res.json()["title"] == PIN_BODY["title"]
    assert lore_received[-1]["path"] == f"/api/v1/campaigns/{campaign_id}/atlas/pins"
    assert lore_received[-1]["body"] == PIN_BODY
    assert lore_received[-1]["authorization"] == headers["Authorization"]
    assert lore_received[-1]["x_user_id"] is None
    assert lore_received[-1]["subject"] == "dm_valeros"


def test_publish_codex_entry_forwards_body_and_bearer(
    client: TestClient, owner, lore_received
) -> None:
    campaign_id, headers = owner
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/codex/entries", json=ENTRY_BODY, headers=headers
    )

    assert res.status_code == 201, res.text
    assert res.json()["entry_id"] == "entry-owner"
    assert lore_received[-1]["path"] == f"/api/v1/campaigns/{campaign_id}/codex/entries"
    assert lore_received[-1]["body"] == ENTRY_BODY
    assert lore_received[-1]["subject"] == "dm_valeros"


def test_create_pin_without_bearer_is_rejected_before_the_owner(
    client: TestClient, owner, lore_received
) -> None:
    campaign_id, _ = owner
    before = len(lore_received)
    res = client.post(f"/api/v1/campaigns/{campaign_id}/atlas/pins", json=PIN_BODY)

    assert res.status_code == 401
    assert len(lore_received) == before


def test_owner_refusal_passes_through_as_403(client: TestClient, owner, lore_reply) -> None:
    campaign_id, headers = owner
    lore_reply["status"] = 403
    res = client.post(f"/api/v1/campaigns/{campaign_id}/atlas/pins", json=PIN_BODY, headers=headers)

    assert res.status_code == 403
    assert res.json() == {"detail": "owner refused"}


def test_owner_server_error_returns_502_not_a_pin(client: TestClient, owner, lore_reply) -> None:
    campaign_id, headers = owner
    lore_reply["status"] = 500
    res = client.post(f"/api/v1/campaigns/{campaign_id}/atlas/pins", json=PIN_BODY, headers=headers)

    assert res.status_code == 502
    assert "pin_id" not in res.text


@pytest.fixture
def lore_down(monkeypatch, game_session_upstream) -> Iterator[TestClient]:
    """Point the gateway at a loopback port where nothing listens."""
    monkeypatch.setenv("CAMPAIGN_LORE_URL", closed_port_url())
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def test_owner_unreachable_returns_503_for_pin_create(lore_down, trusted_ws_issuer) -> None:
    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('dm_valeros')}"}
    campaign = lore_down.post(
        "/api/v1/campaigns",
        json={"title": "Unreachable Lore", "setting": "Astral Void", "system": "5e"},
        headers=headers,
    )
    assert campaign.status_code == 201, campaign.text
    res = lore_down.post(
        f"/api/v1/campaigns/{campaign.json()['id']}/atlas/pins", json=PIN_BODY, headers=headers
    )

    assert res.status_code == 503
    assert res.json()["upstream"] == "campaign_lore"
    assert "pin_id" not in res.text


def test_owner_503_returns_502_for_codex_publish(monkeypatch, client, owner) -> None:
    campaign_id, headers = owner
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("CAMPAIGN_LORE_URL", down_url)
        with TestClient(gateway_app) as gateway_client:
            res = gateway_client.post(
                f"/api/v1/campaigns/{campaign_id}/codex/entries", json=ENTRY_BODY, headers=headers
            )

    assert res.status_code == 502
    assert "entry_id" not in res.text
