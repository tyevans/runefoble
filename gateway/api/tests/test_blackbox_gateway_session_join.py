"""Blackbox tests: a campaign player takes a lobby seat through the gateway (TASK-0889).

The gateway forwards the bearer token and the body to game_session, and game_session checks
`session.participate`. Setup goes through public routes only: the owner creates the campaign
and the session, and the player redeems a campaign invite. Governed by ADR-0001, ADR-0013,
ADR-0014 and ADR-0015.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.campaign_setup import create_owner_session, invite_and_join
from tests.helpers.live_services import closed_port_url

OWNER = "dm-evelyn"
PLAYER = "player-mira"


@pytest.fixture
def client(game_session_upstream: str) -> Iterator[TestClient]:
    """Enter the gateway lifespan after the upstream URL is set, so the proxy sees it."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _seat_body(character_id: str | None = None) -> dict[str, str]:
    return {
        "character_id": character_id or str(uuid4()),
        "character_name": "Mira Thornwake",
        "character_class": "Ranger",
    }


@pytest.fixture
def lobby(client, game_session_upstream, trusted_ws_issuer) -> tuple[str, str]:
    """A campaign that OWNER runs, with PLAYER joined by invite, and one lobby session."""
    owner = _auth(trusted_ws_issuer, OWNER)
    campaign = client.post("/api/v1/campaigns", json={"title": "Lantern Vigil"}, headers=owner)
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    invite_and_join(client, campaign_id, OWNER, PLAYER, issuer=trusted_ws_issuer)
    return campaign_id, create_owner_session(game_session_upstream, owner, campaign_id)


def test_missing_token_is_refused(client) -> None:
    res = client.post(f"/api/v1/sessions/{uuid4()}/join", json=_seat_body())
    assert res.status_code == 401


def test_campaign_player_takes_a_seat_and_the_roster_shows_it(
    client, lobby, trusted_ws_issuer
) -> None:
    _, session_id = lobby
    character_id = str(uuid4())
    seated = client.post(
        f"/api/v1/sessions/{session_id}/join",
        json=_seat_body(character_id),
        headers=_auth(trusted_ws_issuer, PLAYER),
    )
    assert seated.status_code == 200, seated.text

    state = client.get(
        f"/api/v1/sessions/{session_id}", headers=_auth(trusted_ws_issuer, OWNER)
    ).json()
    assert PLAYER in state["participants"]
    assert state["participants"][PLAYER]["character_name"] == "Mira Thornwake"
    assert state["participants"][PLAYER]["character_id"] == character_id


def test_stranger_gets_the_owner_refusal(client, lobby, trusted_ws_issuer) -> None:
    _, session_id = lobby
    res = client.post(
        f"/api/v1/sessions/{session_id}/join",
        json=_seat_body(),
        headers=_auth(trusted_ws_issuer, "stranger-quill"),
    )
    assert res.status_code == 403
    assert isinstance(res.json()["detail"], str)

    state = client.get(
        f"/api/v1/sessions/{session_id}", headers=_auth(trusted_ws_issuer, OWNER)
    ).json()
    assert "stranger-quill" not in state["participants"]


def test_bad_body_is_refused_by_the_owner(client, lobby, trusted_ws_issuer) -> None:
    _, session_id = lobby
    res = client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={"character_name": "Mira"},
        headers=_auth(trusted_ws_issuer, PLAYER),
    )
    assert res.status_code == 422


def test_owner_unreachable_returns_503(lobby, monkeypatch, trusted_ws_issuer) -> None:
    _, session_id = lobby
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())
    with TestClient(gateway_app) as gateway_client:
        res = gateway_client.post(
            f"/api/v1/sessions/{session_id}/join",
            json=_seat_body(),
            headers=_auth(trusted_ws_issuer, PLAYER),
        )
    assert res.status_code == 503
    assert res.json()["upstream"] == "game_session"
