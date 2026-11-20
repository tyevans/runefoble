"""Blackbox tests: a seated player rolls dice through the gateway (TASK-0951).

The gateway forwards the bearer token and the roll body to game_session. The owner checks
`session.participate`, evaluates the roll, and records a `DiceRolled` event. Setup goes through
public routes only: the owner creates the campaign and the session, the player redeems a campaign
invite, and the player takes a lobby seat. The chronicle read shows the stored roll. Governed by
ADR-0013, ADR-0014 and ADR-0015.
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
STRANGER = "stranger-quill"
ROLLER_NAME = "Mira Thornwake"


@pytest.fixture
def client(game_session_upstream: str) -> Iterator[TestClient]:
    """Enter the gateway lifespan after the upstream URL is set, so the proxy sees it."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _roll_body(formula: str = "1d20") -> dict[str, str]:
    return {"formula": formula, "roller_name": ROLLER_NAME, "roll_type": "attack"}


@pytest.fixture
def seated_session(client, game_session_upstream, trusted_ws_issuer) -> str:
    """A lobby session that OWNER runs, with PLAYER joined by invite and seated with a character."""
    owner = _auth(trusted_ws_issuer, OWNER)
    campaign = client.post("/api/v1/campaigns", json={"title": "Roll Night"}, headers=owner)
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    invite_and_join(client, campaign_id, OWNER, PLAYER, issuer=trusted_ws_issuer)
    session_id = create_owner_session(game_session_upstream, owner, campaign_id)
    seated = client.post(
        f"/api/v1/sessions/{session_id}/join",
        json={
            "character_id": str(uuid4()),
            "character_name": ROLLER_NAME,
            "character_class": "Ranger",
        },
        headers=_auth(trusted_ws_issuer, PLAYER),
    )
    assert seated.status_code == 200, seated.text
    return session_id


def test_missing_token_is_refused(client) -> None:
    res = client.post(f"/api/v1/sessions/{uuid4()}/roll", json=_roll_body())
    assert res.status_code == 401


def test_seated_player_rolls_and_the_owner_records_the_roll(
    client, seated_session, trusted_ws_issuer
) -> None:
    res = client.post(
        f"/api/v1/sessions/{seated_session}/roll",
        json=_roll_body("1d20"),
        headers=_auth(trusted_ws_issuer, PLAYER),
    )
    assert res.status_code == 200, res.text
    reply = res.json()
    assert reply["roller_name"] == ROLLER_NAME
    assert reply["formula"] == "1d20"
    assert 1 <= reply["total"] <= 20
    assert reply["rolls"] == [reply["total"]]

    feed = client.get(
        f"/api/v1/sessions/{seated_session}/events", headers=_auth(trusted_ws_issuer, OWNER)
    )
    assert feed.status_code == 200, feed.text
    rolls = [entry for entry in feed.json() if entry["kind"] == "dice_roll"]
    assert len(rolls) == 1
    assert rolls[0]["speaker"] == ROLLER_NAME
    assert rolls[0]["text"] == f"1d20 = {reply['total']}"


def test_stranger_gets_the_owner_refusal(client, seated_session, trusted_ws_issuer) -> None:
    res = client.post(
        f"/api/v1/sessions/{seated_session}/roll",
        json=_roll_body(),
        headers=_auth(trusted_ws_issuer, STRANGER),
    )
    assert res.status_code == 403
    assert isinstance(res.json()["detail"], str)


def test_bad_formula_is_refused_by_the_owner(client, seated_session, trusted_ws_issuer) -> None:
    res = client.post(
        f"/api/v1/sessions/{seated_session}/roll",
        json=_roll_body("not-a-formula"),
        headers=_auth(trusted_ws_issuer, PLAYER),
    )
    assert res.status_code == 422


def test_owner_unreachable_returns_503(seated_session, monkeypatch, trusted_ws_issuer) -> None:
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())
    with TestClient(gateway_app) as gateway_client:
        res = gateway_client.post(
            f"/api/v1/sessions/{seated_session}/roll",
            json=_roll_body(),
            headers=_auth(trusted_ws_issuer, PLAYER),
        )
    assert res.status_code == 503
    assert res.json()["upstream"] == "game_session"
