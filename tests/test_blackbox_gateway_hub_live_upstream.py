"""Blackbox frontdoor test: gateway hub views return live upstream data (TASK-0646).

The gateway is called through its public HTTP routes. The upstream campaign-lore and
campaign-analytics services are real HTTP stand-ins on loopback ports (ADR-0014). Each
stand-in records the headers it receives and verifies the forwarded bearer token with the
same test issuer that the gateway trusts (ADR-0015 c, TASK-0531, TASK-0536). A token the
upstream cannot verify gets 401, which the gateway passes through. The gateway forwards the
caller's verified bearer token and no user header.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_auth.principal import authenticate_authorization
from runefoble_auth.zitadel import ZitadelAuthService

from tests.helpers.live_services import serve

LIVE_PIN = {
    "pin_id": "pin-live",
    "title": "Star-Eater Gate",
    "layer": "continental",
    "coordinates": {"x": 10, "y": 20},
}
LIVE_CODEX_ENTRY = {"entry_id": "entry-live", "title": "The Star-Eater Relic"}


def _recording_upstream(received: list[dict[str, Any]], verifier: ZitadelAuthService) -> FastAPI:
    """Return an upstream stand-in that records each request and verifies its bearer token."""
    app = FastAPI()

    @app.get("/{path:path}")
    def _live(path: str, request: Request) -> Any:
        principal = authenticate_authorization(verifier, request.headers.get("authorization"))
        received.append(
            {
                "path": request.url.path,
                "authorization": request.headers.get("authorization"),
                "x_user_id": request.headers.get("x-user-id"),
                "subject": principal.user_id,
            }
        )
        if path.endswith("/atlas"):
            return {"campaign_id": "c", "pins": [LIVE_PIN], "territories": []}
        if path.endswith("/codex/entries"):
            return [LIVE_CODEX_ENTRY]
        return {"campaign_id": "c", "total_combat_turns": 3}

    return app


@pytest.fixture
def upstream_received(monkeypatch, signing_issuer) -> Iterator[dict[str, list[dict[str, Any]]]]:
    """Serve recording stand-ins for campaign_lore and campaign_analytics, and set their URLs.

    Both stand-ins verify bearer tokens with the test issuer that the gateway trusts.
    """
    lore_seen: list[dict[str, Any]] = []
    analytics_seen: list[dict[str, Any]] = []
    with (
        serve(_recording_upstream(lore_seen, signing_issuer.verifier())) as lore_url,
        serve(_recording_upstream(analytics_seen, signing_issuer.verifier())) as analytics_url,
    ):
        monkeypatch.setenv("CAMPAIGN_LORE_URL", lore_url)
        monkeypatch.setenv("CAMPAIGN_ANALYTICS_URL", analytics_url)
        yield {"lore": lore_seen, "analytics": analytics_seen}


@pytest.fixture
def client(upstream_received, game_session_upstream) -> Iterator[TestClient]:
    """Run the gateway lifespan after the upstream URLs are set, so clients see them."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def owner(client: TestClient, trusted_ws_issuer) -> tuple[str, dict[str, str]]:
    """Create a campaign through the public frontdoor. Return its id and the owner's headers."""
    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('dm_valeros')}"}
    res = client.post(
        "/api/v1/campaigns",
        json={
            "title": "Tomb of the Star-Eater",
            "setting": "Astral Void",
            "system": "5e",
            "description": "Live data.",
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"], headers


def test_atlas_returns_upstream_pins_and_forwards_bearer_only(
    client: TestClient, owner, upstream_received
) -> None:
    campaign_id, headers = owner
    received = upstream_received["lore"]
    res = client.get(
        f"/api/v1/campaigns/{campaign_id}/atlas",
        headers={**headers, "X-User-Id": "spoofed-user"},
    )

    assert res.status_code == 200
    assert [pin["title"] for pin in res.json()["pins"]] == ["Star-Eater Gate"]
    assert received[-1]["path"] == f"/api/v1/campaigns/{campaign_id}/atlas"
    assert received[-1]["authorization"] == headers["Authorization"]
    assert received[-1]["x_user_id"] is None
    assert received[-1]["subject"] == "dm_valeros"


def test_codex_returns_upstream_entries_and_forwards_bearer_only(
    client: TestClient, owner, upstream_received
) -> None:
    campaign_id, headers = owner
    received = upstream_received["lore"]
    res = client.get(f"/api/v1/campaigns/{campaign_id}/codex", headers=headers)

    assert res.status_code == 200
    assert res.json() == [LIVE_CODEX_ENTRY]
    assert received[-1]["path"] == f"/api/v1/campaigns/{campaign_id}/codex/entries"
    assert received[-1]["authorization"] == headers["Authorization"]
    assert received[-1]["x_user_id"] is None


def test_heatmap_forwards_bearer_only_to_analytics(
    client: TestClient, owner, upstream_received
) -> None:
    campaign_id, headers = owner
    received = upstream_received["analytics"]
    res = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/heatmap", headers=headers)

    assert res.status_code == 200
    assert received[-1]["path"] == f"/api/v1/analytics/campaigns/{campaign_id}/heatmap"
    assert received[-1]["authorization"] == headers["Authorization"]
    assert received[-1]["x_user_id"] is None
