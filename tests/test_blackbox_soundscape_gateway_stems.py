"""Blackbox frontdoor tests for the gateway stem volume proxy (TASK-0436).

The gateway forwards `POST /api/v1/soundscape/stems/volume` to the soundscape service. The owner
checks the Zanzibar session control permission (or campaign run_session) and holds the mixer state.

Governed by:
- ADR-0001: Google Zanzibar Fine-Grained Authorization via SpiceDB
- ADR-0015: Verified bearer tokens; the gateway answers 502/503 on owner failure, never a substitute
- Hard Invariant 1: SpiceDB Zanzibar schema authorization
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from soundscape.main import app as soundscape_app

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.ws_identity import SIGNING_ISSUER


@pytest.fixture(autouse=True)
def soundscape_service(monkeypatch) -> Iterator[str]:
    """Run the real soundscape service on a loopback port and point the gateway at it."""
    with serve(soundscape_app) as url:
        monkeypatch.setenv("RUNEFOBLE_SOUNDSCAPE_URL", url)
        yield url


def _auth(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def _stems_body(session_id: str) -> dict[str, Any]:
    return {"session_id": session_id, "stem_volumes": {"melody": 0.5}}


@pytest.fixture
def client(trusted_ws_issuer, game_session_upstream) -> Iterator[TestClient]:
    """Run the gateway lifespan after the soundscape URL is set, so the client sees it."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


@pytest.fixture
def session_id(client: TestClient) -> str:
    """Create a campaign with a player and a session through public frontdoors."""
    camp = client.post(
        "/api/v1/campaigns",
        json={
            "title": "Mixing Desk",
            "setting": "Underdark Caverns",
            "system": "5e",
            "description": "Stem volume proxy testing campaign.",
        },
        headers=_auth("dm_evelyn"),
    )
    assert camp.status_code == 201
    cid = camp.json()["id"]

    role = client.post(
        f"/api/v1/campaigns/{cid}/roles",
        json={"user_id": "player_valeros", "role": "player"},
        headers=_auth("dm_evelyn"),
    )
    assert role.status_code == 200

    sess = client.post(
        f"/api/v1/campaigns/{cid}/sessions",
        json={"title": "Echoing Depths"},
        headers=_auth("dm_evelyn"),
    )
    assert sess.status_code == 201
    return sess.json()["id"]


def test_openapi_exposes_stem_volume_route(client: TestClient) -> None:
    """The gateway document lists the stem volume route for the Swagger UI hub."""
    res = client.get("/openapi.json")
    assert res.status_code == 200
    assert "post" in res.json()["paths"]["/api/v1/soundscape/stems/volume"]


def test_stem_volume_dm_updates_channels_through_gateway(
    client: TestClient, session_id: str
) -> None:
    """The DM sets a stem volume, and the gateway returns the owner's channel state."""
    res = client.post(
        "/api/v1/soundscape/stems/volume",
        headers=_auth("dm_evelyn"),
        json=_stems_body(session_id),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["session_id"] == session_id
    assert data["stem_channels"]["melody"] == 0.5


def test_stem_volume_player_forbidden(client: TestClient, session_id: str) -> None:
    """A player lacks session control, so the owner refuses the volume change with 403."""
    res = client.post(
        "/api/v1/soundscape/stems/volume",
        headers=_auth("player_valeros"),
        json=_stems_body(session_id),
    )
    assert res.status_code == 403
    assert "Forbidden" in res.json()["detail"]


def test_stem_volume_stranger_forbidden(client: TestClient, session_id: str) -> None:
    """A user outside the campaign receives 403 and the owner state stays unchanged."""
    res = client.post(
        "/api/v1/soundscape/stems/volume",
        headers=_auth("stranger_bob"),
        json=_stems_body(session_id),
    )
    assert res.status_code == 403


def test_stem_volume_requires_bearer_token(client: TestClient, session_id: str) -> None:
    """Without a verified token the gateway answers 401 and never reaches the owner."""
    res = client.post("/api/v1/soundscape/stems/volume", json=_stems_body(session_id))
    assert res.status_code == 401


def test_stem_volume_returns_503_when_soundscape_is_unreachable(
    client: TestClient, session_id: str, monkeypatch
) -> None:
    """A down owner gives 503. The gateway never answers from its own state."""
    monkeypatch.setenv("RUNEFOBLE_SOUNDSCAPE_URL", closed_port_url())
    with TestClient(gateway_app) as down_client:
        res = down_client.post(
            "/api/v1/soundscape/stems/volume",
            headers=_auth("dm_evelyn"),
            json=_stems_body(session_id),
        )
    assert res.status_code == 503
