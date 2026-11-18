"""Blackbox tests for the gateway proxy identity and error contract (TASK-0536, TASK-0580).

The gateway forwards the caller's verified bearer token to an owning service. It
never forwards a user header. An unreachable service returns 503. A failing service
(upstream 5xx) returns 502. An upstream 4xx passes through. The upstream is a stand-in
on a loopback port (ADR-0014). It records the headers that it receives. Nothing patches
the HTTP client.

Governed by:
- TASK-0536: Gateway Proxies Forward the Verified Bearer Token
- TASK-0580: Shared Typed Service Client for Gateway Proxies
- ADR-0015: Audit remediation decisions (no substitute values on upstream failure)
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient
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
            "x_forwarded_foo": request.headers.get("x-forwarded-foo"),
            "service_credential": request.headers.get("x-runefoble-service-credential"),
            "traceparent": request.headers.get("traceparent"),
        }

    return app


@contextmanager
def gateway(monkeypatch: pytest.MonkeyPatch, **upstream_urls: str) -> Iterator[TestClient]:
    """Set upstream URL variables, then run the gateway lifespan so it builds its clients."""
    for name, url in upstream_urls.items():
        monkeypatch.setenv(name, url)
    with TestClient(gateway_app) as client:
        yield client


def _create_campaign(client: TestClient, trusted_ws_issuer) -> tuple[str, dict[str, str]]:
    """Create a campaign through the public frontdoor. Return its id and the owner's headers."""
    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('dm_valeros')}"}
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Proxy Contract", "setting": "Test", "system": "5e", "description": "x"},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()["id"], headers


def test_proxy_forwards_bearer_token_and_no_user_header(
    monkeypatch, trusted_ws_issuer, game_session_upstream
) -> None:
    """The upstream receives the same Authorization value and no X-User-Id."""
    with (
        serve(_echo_upstream()) as lore_url,
        gateway(monkeypatch, CAMPAIGN_LORE_URL=lore_url) as client,
    ):
        campaign_id, headers = _create_campaign(client, trusted_ws_issuer)
        res = client.get(
            f"/api/v1/campaigns/{campaign_id}/atlas",
            headers={**headers, "X-User-Id": "spoofed-user"},
        )

    assert res.status_code == 200
    echoed = res.json()
    assert echoed["authorization"] == headers["Authorization"]
    assert echoed["x_user_id"] is None


def test_proxy_sends_the_service_credential_and_trace_context(
    monkeypatch, trusted_ws_issuer, game_session_upstream
) -> None:
    """Every proxied call presents the service credential (ADR-0015 e) and a traceparent."""
    with (
        serve(_echo_upstream()) as lore_url,
        gateway(monkeypatch, CAMPAIGN_LORE_URL=lore_url) as client,
    ):
        campaign_id, headers = _create_campaign(client, trusted_ws_issuer)
        res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)

    assert res.status_code == 200
    echoed = res.json()
    assert echoed["service_credential"] == os.environ["RUNEFOBLE_SERVICE_CREDENTIAL"]
    assert echoed["traceparent"] is not None
    assert echoed["traceparent"].startswith("00-")


def test_soundscape_proxy_forwards_bearer_token(monkeypatch, trusted_ws_issuer) -> None:
    """A soundscape proxy route forwards the verified bearer token as well."""
    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('player_valeros')}"}
    with (
        serve(_echo_upstream()) as soundscape_url,
        gateway(monkeypatch, SOUNDSCAPE_SERVICE_URL=soundscape_url) as client,
    ):
        res = client.get("/api/v1/soundscape/tension?session_id=session-1", headers=headers)

    assert res.status_code == 200
    echoed = res.json()
    assert echoed["path"] == "/api/v1/soundscape/tension"
    assert echoed["authorization"] == headers["Authorization"]
    assert echoed["x_user_id"] is None


def test_client_header_is_not_forwarded_to_upstream(monkeypatch, trusted_ws_issuer) -> None:
    """Headers that the client sends are never copied to the owning service."""
    headers = {"Authorization": f"Bearer {trusted_ws_issuer.mint('player_valeros')}"}
    with (
        serve(_echo_upstream()) as soundscape_url,
        gateway(monkeypatch, SOUNDSCAPE_SERVICE_URL=soundscape_url) as client,
    ):
        res = client.get(
            "/api/v1/soundscape/tension?session_id=session-1",
            headers={**headers, "X-Forwarded-Foo": "injected"},
        )

    assert res.status_code == 200
    assert res.json()["x_forwarded_foo"] is None


def test_upstream_403_passes_through_unchanged(
    monkeypatch, trusted_ws_issuer, game_session_upstream
) -> None:
    """An upstream 403 reaches the client as 403 with the upstream body."""
    with (
        serve(unavailable_app(403)) as lore_url,
        gateway(monkeypatch, CAMPAIGN_LORE_URL=lore_url) as client,
    ):
        campaign_id, headers = _create_campaign(client, trusted_ws_issuer)
        res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)

    assert res.status_code == 403
    assert res.json() == {"detail": "service maintenance"}


def test_upstream_5xx_returns_502(monkeypatch, trusted_ws_issuer, game_session_upstream) -> None:
    """An upstream 503 returns 502 with a fixed message, not a success body."""
    with (
        serve(unavailable_app(503)) as lore_url,
        gateway(monkeypatch, CAMPAIGN_LORE_URL=lore_url) as client,
    ):
        campaign_id, headers = _create_campaign(client, trusted_ws_issuer)
        res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)

    assert res.status_code == 502
    assert res.json() == {"detail": "Upstream service is unavailable", "upstream": "campaign_lore"}
    assert "service maintenance" not in res.text


def test_unreachable_upstream_returns_503(
    monkeypatch, trusted_ws_issuer, game_session_upstream
) -> None:
    """A connection refused by the upstream returns 503 with no canned payload."""
    with gateway(monkeypatch, CAMPAIGN_LORE_URL=closed_port_url()) as client:
        campaign_id, headers = _create_campaign(client, trusted_ws_issuer)
        res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)

    assert res.status_code == 503
    assert "Sunken Citadel" not in res.text
    assert res.json() == {"detail": "Upstream service is unavailable", "upstream": "campaign_lore"}


def test_unconfigured_upstream_returns_503(
    monkeypatch, trusted_ws_issuer, game_session_upstream
) -> None:
    """An empty upstream URL means no client exists, so the proxy returns 503 with no payload."""
    with gateway(monkeypatch, CAMPAIGN_LORE_URL="") as client:
        campaign_id, headers = _create_campaign(client, trusted_ws_issuer)
        res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)

    assert res.status_code == 503
    assert res.json()["upstream"] == "campaign_lore"


def test_non_json_success_body_returns_502(
    monkeypatch, trusted_ws_issuer, game_session_upstream
) -> None:
    """An upstream 200 with a non-JSON body returns 502, not an empty success."""
    broken = FastAPI()

    @broken.get("/{path:path}")
    def _text(path: str) -> PlainTextResponse:
        return PlainTextResponse("not json", status_code=200)

    with serve(broken) as lore_url, gateway(monkeypatch, CAMPAIGN_LORE_URL=lore_url) as client:
        campaign_id, headers = _create_campaign(client, trusted_ws_issuer)
        res = client.get(f"/api/v1/campaigns/{campaign_id}/atlas", headers=headers)

    assert res.status_code == 502
