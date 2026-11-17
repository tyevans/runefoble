"""Blackbox tests for the gateway proxy identity and error contract (TASK-0536).

The gateway forwards the caller's verified bearer token to an owning service. It
never forwards a user header. An unreachable or failing upstream returns 502. An
upstream 4xx passes through. The upstream is a stand-in on a loopback port
(ADR-0014). It records the headers that it receives. Nothing patches the HTTP client.

Governed by:
- TASK-0536: Gateway Proxies Forward the Verified Bearer Token
- ADR-0015: Audit remediation decisions (no substitute values on upstream failure)
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from gateway_api.campaign_store import campaign_store
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app


def _echo_upstream() -> FastAPI:
    """Return a stand-in upstream that reports the headers and path it received."""
    app = FastAPI()

    @app.get("/{path:path}")
    def _echo(request: Request) -> dict[str, Any]:
        return {
            "path": request.url.path,
            "authorization": request.headers.get("authorization"),
            "x_user_id": request.headers.get("x-user-id"),
        }

    return app


@pytest.fixture(autouse=True)
def reset_store() -> Iterator[None]:
    campaign_store.reset()
    yield
    campaign_store.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(gateway_app)


@pytest.fixture
def owner_campaign(client: TestClient, signing_issuer) -> tuple[str, dict[str, str]]:
    """Create a campaign through the public frontdoor. Return its id and the owner's headers."""
    headers = {"Authorization": f"Bearer {signing_issuer.mint('dm_valeros')}"}
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Proxy Contract", "setting": "Test", "system": "5e", "description": "x"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"], headers


def test_proxy_forwards_bearer_token_and_no_user_header(
    client: TestClient, owner_campaign, monkeypatch
) -> None:
    """The upstream receives the same Authorization value and no X-User-Id."""
    campaign_id, headers = owner_campaign
    with serve(_echo_upstream()) as lore_url:
        monkeypatch.setenv("CAMPAIGN_LORE_URL", lore_url)
        res = client.get(
            f"/api/v1/campaigns/{campaign_id}/atlas",
            headers={**headers, "X-User-Id": "spoofed-user"},
        )

    assert res.status_code == 200
    echoed = res.json()
    assert echoed["authorization"] == headers["Authorization"]
    assert echoed["x_user_id"] is None


def test_soundscape_proxy_forwards_bearer_token(
    client: TestClient, signing_issuer, monkeypatch
) -> None:
    """A soundscape proxy route forwards the verified bearer token as well."""
    headers = {"Authorization": f"Bearer {signing_issuer.mint('player_valeros')}"}
    with serve(_echo_upstream()) as soundscape_url:
        monkeypatch.setenv("SOUNDSCAPE_SERVICE_URL", soundscape_url)
        res = client.get("/api/v1/soundscape/tension?session_id=session-1", headers=headers)

    assert res.status_code == 200
    echoed = res.json()
    assert echoed["path"] == "/api/v1/soundscape/tension"
    assert echoed["authorization"] == headers["Authorization"]
    assert echoed["x_user_id"] is None


def test_upstream_403_passes_through_unchanged(
    client: TestClient, owner_campaign, monkeypatch
) -> None:
    """An upstream 403 reaches the client as 403."""
    campaign_id, headers = owner_campaign
    with serve(unavailable_app(403)) as lore_url:
        monkeypatch.setenv("CAMPAIGN_LORE_URL", lore_url)
        res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)

    assert res.status_code == 403


def test_upstream_5xx_returns_502(client: TestClient, owner_campaign, monkeypatch) -> None:
    """An upstream 503 returns 502 with a fixed message, not a success body."""
    campaign_id, headers = owner_campaign
    with serve(unavailable_app(503)) as lore_url:
        monkeypatch.setenv("CAMPAIGN_LORE_URL", lore_url)
        res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)

    assert res.status_code == 502
    assert "service maintenance" not in res.text


def test_unreachable_upstream_returns_502(client: TestClient, owner_campaign, monkeypatch) -> None:
    """A connection refused by the upstream returns 502 with no canned payload."""
    campaign_id, headers = owner_campaign
    monkeypatch.setenv("CAMPAIGN_LORE_URL", closed_port_url())
    res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)

    assert res.status_code == 502
    assert "Sunken Citadel" not in res.text
    assert res.json()["detail"] == "Upstream service is unavailable"
