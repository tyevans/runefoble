"""Blackbox tests: gateway tabletop session routes proxy to game_session (TASK-0581).

The gateway is called through its public HTTP routes. Requests without a verified bearer
token must fail before any upstream call. A session that the caller cannot observe in
SpiceDB must be refused, and the gateway must not answer with canned session data.
Governed by ADR-0001 (Zanzibar object checks), ADR-0007 (gateway holds no session state),
and ADR-0015 (identity from the verified token only).
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.campaign_setup import create_owner_session
from tests.helpers.live_services import closed_port_url


@pytest.fixture
def client(game_session_upstream: str) -> Iterator[TestClient]:
    """Enter the gateway lifespan after the upstream URL is set, so the proxy sees it."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


SESSION_ROUTES = [
    ("GET", "/api/v1/sessions/{sid}", None),
    ("POST", "/api/v1/sessions/{sid}/start", None),
    ("POST", "/api/v1/sessions/{sid}/hot-swap", {"characterId": str(uuid4())}),
    ("POST", "/api/v1/sessions/{sid}/turns/advance", None),
    ("POST", "/api/v1/sessions/{sid}/dm-override", {"action": "pause"}),
    ("POST", "/api/v1/sessions/{sid}/atmosphere", {"location_name": "Crypt"}),
]


@pytest.mark.parametrize(("method", "path", "body"), SESSION_ROUTES)
def test_missing_token_is_refused_before_any_upstream_call(client, method, path, body) -> None:
    res = client.request(method, path.format(sid=uuid4()), json=body)
    assert res.status_code == 401


@pytest.mark.parametrize(("method", "path", "body"), SESSION_ROUTES)
def test_unobservable_session_is_refused_and_no_canned_state_is_returned(
    client, trusted_ws_issuer, method, path, body
) -> None:
    """A session with no campaign link in SpiceDB gives the caller no observe or control right."""
    res = client.request(
        method,
        path.format(sid=uuid4()),
        json=body,
        headers=_auth(trusted_ws_issuer, "dm-evelyn"),
    )
    assert res.status_code == 403
    assert res.json()["detail"]["error"] == "permission_denied"


@pytest.fixture
def owned_session(client, game_session_upstream, trusted_ws_issuer):
    """A campaign owned by dm-evelyn, with one live session linked to it."""
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    campaign = client.post("/api/v1/campaigns", json={"title": "Tomb"}, headers=owner)
    assert campaign.status_code == 201, campaign.text
    session_id = create_owner_session(game_session_upstream, owner, campaign.json()["id"])
    return owner, session_id


def test_gateway_reads_the_session_the_owner_created(client, owned_session) -> None:
    owner, session_id = owned_session
    res = client.get(f"/api/v1/sessions/{session_id}", headers=owner)
    assert res.status_code == 200, res.text
    assert res.json()["session_id"] == session_id
    assert res.json()["status"] == "lobby"


def test_start_then_advance_turn_is_seen_on_the_next_read(client, owned_session) -> None:
    owner, session_id = owned_session
    assert client.post(f"/api/v1/sessions/{session_id}/start", headers=owner).status_code == 200
    advanced = client.post(f"/api/v1/sessions/{session_id}/turns/advance", headers=owner)
    assert advanced.status_code == 200, advanced.text
    state = client.get(f"/api/v1/sessions/{session_id}", headers=owner).json()
    assert state["current_turn"] == 2


def test_dm_override_and_atmosphere_are_seen_on_the_next_read(client, owned_session) -> None:
    owner, session_id = owned_session
    override = client.post(
        f"/api/v1/sessions/{session_id}/dm-override",
        json={"action": "pause_encounter", "reason": "DM narrative pause"},
        headers=owner,
    )
    assert override.status_code == 200, override.text
    atmosphere = client.post(
        f"/api/v1/sessions/{session_id}/atmosphere",
        json={"location_name": "Crypt", "lighting": "Dim"},
        headers=owner,
    )
    assert atmosphere.status_code == 200, atmosphere.text

    state = client.get(f"/api/v1/sessions/{session_id}", headers=owner).json()
    assert state["dm_overrides"][0]["action"] == "pause_encounter"
    assert state["atmosphere"]["lighting"] == "Dim"


def test_owner_unreachable_returns_503_after_the_gateway_check(
    owned_session, monkeypatch, trusted_ws_issuer
) -> None:
    owner, session_id = owned_session
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())
    with TestClient(gateway_app) as gateway_client:
        res = gateway_client.get(f"/api/v1/sessions/{session_id}", headers=owner)
    assert res.status_code == 503
    assert res.json()["upstream"] == "game_session"
