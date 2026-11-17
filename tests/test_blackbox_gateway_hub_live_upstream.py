"""Blackbox frontdoor test: gateway hub views return live upstream data (TASK-0646).

The gateway is called through its public HTTP routes. The upstream lore and analytics
services are replaced at the HTTP transport boundary only (httpx.MockTransport).
Governing: ADR-0015 (b) and (c), Hard Invariant 7.
"""

from __future__ import annotations

import types
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app
from gateway_api.routers import hub_views

LIVE_PIN = {
    "pin_id": "pin-live",
    "title": "Star-Eater Gate",
    "layer": "continental",
    "coordinates": {"x": 10, "y": 20},
}


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.fixture(autouse=True)
def reset_store():
    campaign_store.reset()
    yield


@pytest.fixture
def upstream_calls(monkeypatch) -> list[httpx.Request]:
    """Route upstream proxy calls to a recording transport that returns live payloads."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path.endswith("/atlas"):
            body: Any = {"campaign_id": "c", "pins": [LIVE_PIN], "territories": []}
        else:
            body = []
        return httpx.Response(200, json=body)

    real_client = httpx.AsyncClient

    def client_factory(**kwargs: Any) -> httpx.AsyncClient:
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(hub_views, "httpx", types.SimpleNamespace(AsyncClient=client_factory))
    return calls


def _create_campaign(client: TestClient, issuer) -> str:
    res = client.post(
        "/api/v1/campaigns",
        json={
            "title": "Tomb of the Star-Eater",
            "setting": "Astral Void",
            "system": "5e",
            "description": "Live data.",
        },
        headers=_auth(issuer, "dm_valeros"),
    )
    assert res.status_code == 201
    return res.json()["id"]


def test_atlas_returns_upstream_pins_and_forwards_verified_user(
    signing_issuer, upstream_calls: list[httpx.Request]
) -> None:
    client = TestClient(gateway_app)
    campaign_id = _create_campaign(client, signing_issuer)

    res = client.get(
        f"/api/v1/campaigns/{campaign_id}/atlas", headers=_auth(signing_issuer, "dm_valeros")
    )

    assert res.status_code == 200
    assert [pin["title"] for pin in res.json()["pins"]] == ["Star-Eater Gate"]
    assert upstream_calls, "the gateway must call the campaign-lore service"
    assert upstream_calls[-1].headers["x-user-id"] == "dm_valeros"


def test_codex_returns_upstream_entries_and_forwards_verified_user(
    signing_issuer, upstream_calls: list[httpx.Request]
) -> None:
    client = TestClient(gateway_app)
    campaign_id = _create_campaign(client, signing_issuer)

    res = client.get(
        f"/api/v1/campaigns/{campaign_id}/codex", headers=_auth(signing_issuer, "dm_valeros")
    )

    assert res.status_code == 200
    assert res.json() == []
    assert upstream_calls[-1].url.path == f"/api/v1/campaigns/{campaign_id}/codex/entries"
    assert upstream_calls[-1].headers["x-user-id"] == "dm_valeros"
