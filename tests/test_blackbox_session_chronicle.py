"""Blackbox tests: session chronicle feed and absentee recap read routes (TASK-0641).

Setup and assertions use only public HTTP frontdoors: campaign creation, session creation,
join, start, leave, and the autopilot stand-in turn. The Watcher runs as a local double on a
real socket. The gateway read routes must refuse callers without a token and callers with no
observe right. An empty session must return empty collections, not an error.
Governed by ADR-0001 (Zanzibar object checks), ADR-0011 (read projection over the event
stream), ADR-0015 (no canned payloads; identity from the verified token), and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.game_session_app import session_app
from tests.helpers.stand_in_policy import create_character
from tests.helpers.watcher_double import (
    STAND_IN_ACTION_BODY,
    serve_watcher_double,
    watcher_stand_in_app,
)
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def gateway(game_session_upstream: str) -> Iterator[TestClient]:
    """Enter the gateway lifespan after game_session is served, so the proxy reaches it."""
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _owned_session(gateway: TestClient, upstream: str, owner: dict[str, str]) -> str:
    """Create a campaign through the gateway, then a session in it through game_session."""
    campaign = gateway.post("/api/v1/campaigns", json={"title": "Tomb"}, headers=owner)
    assert campaign.status_code == 201, campaign.text
    created = httpx.post(
        f"{upstream}/api/v1/campaigns/{campaign.json()['id']}/sessions",
        json={"title": "Crypt"},
        headers=owner,
        timeout=5.0,
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _absent_player_with_stand_in_turn(
    gateway: TestClient,
    upstream: str,
    issuer,
    monkeypatch: pytest.MonkeyPatch,
    character_url: str,
) -> tuple[dict[str, str], str]:
    """Run a session where a player leaves and an autopilot stand-in turn is recorded."""
    owner = _auth(issuer, "dm-evelyn")
    session_id = _owned_session(gateway, upstream, owner)
    joined = httpx.post(
        f"{upstream}/api/v1/sessions/{session_id}/join",
        json={
            "character_id": create_character(character_url, "dm-evelyn"),
            "character_name": "Kyra",
            "character_class": "Cleric",
        },
        headers=owner,
        timeout=5.0,
    )
    assert joined.status_code == 200, joined.text
    started = httpx.post(
        f"{upstream}/api/v1/sessions/{session_id}/start", headers=owner, timeout=5.0
    )
    assert started.status_code == 200, started.text
    left = httpx.post(
        f"{upstream}/api/v1/sessions/{session_id}/leave",
        json={"reason": "late arrival"},
        headers=owner,
        timeout=5.0,
    )
    assert left.status_code == 200, left.text

    with serve_watcher_double(watcher_stand_in_app(body=STAND_IN_ACTION_BODY)) as watcher_url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", watcher_url)
        turn = httpx.post(
            f"{upstream}/api/v1/sessions/{session_id}/turns/auto-pilot",
            json={"penalties": ["drunk"]},
            headers=owner,
            timeout=10.0,
        )
    assert turn.status_code == 200, turn.text
    return owner, session_id


SESSION_READ_ROUTES = [
    "/api/v1/sessions/{sid}/events",
    "/api/v1/sessions/{sid}/absentee-recap",
]


@pytest.mark.parametrize("path", SESSION_READ_ROUTES)
def test_missing_token_is_refused_before_any_upstream_call(gateway, path: str) -> None:
    res = gateway.get(path.format(sid=uuid4()))
    assert res.status_code == 401


@pytest.mark.parametrize("path", SESSION_READ_ROUTES)
def test_caller_without_observe_right_is_refused(gateway, trusted_ws_issuer, path: str) -> None:
    res = gateway.get(path.format(sid=uuid4()), headers=_auth(trusted_ws_issuer, "stranger"))
    assert res.status_code == 403
    assert res.json()["detail"]["error"] == "permission_denied"


@pytest.mark.parametrize("path", SESSION_READ_ROUTES)
def test_owner_refuses_a_stranger_on_an_existing_session(
    gateway, game_session_upstream, trusted_ws_issuer, path: str
) -> None:
    """The owner checks `session.observe` itself, so a direct call is refused too (TASK-0809)."""
    owner = _auth(trusted_ws_issuer, "dm_dora")
    session_id = _owned_session(gateway, game_session_upstream, owner)
    url = f"{game_session_upstream}{path.format(sid=session_id)}"

    refused = httpx.get(url, headers=_auth(trusted_ws_issuer, "stranger"), timeout=5.0)
    assert refused.status_code == 403
    allowed = httpx.get(url, headers=owner, timeout=5.0)
    assert allowed.status_code == 200, allowed.text


def test_feed_lists_the_stand_in_action_with_its_speaker_and_line(
    gateway, game_session_upstream, trusted_ws_issuer, monkeypatch, live_character_sheet
) -> None:
    owner, session_id = _absent_player_with_stand_in_turn(
        gateway, game_session_upstream, trusted_ws_issuer, monkeypatch, live_character_sheet
    )
    res = gateway.get(f"/api/v1/sessions/{session_id}/events", headers=owner)
    assert res.status_code == 200, res.text
    stand_in_entries = [e for e in res.json() if e["kind"] == "stand_in_action"]
    assert len(stand_in_entries) == 1
    entry = stand_in_entries[0]
    assert entry["speaker"] == "Kyra"
    assert entry["text"] == "Configured Watcher says hello."
    assert entry["action_type"] == "attack"
    assert entry["penalties"] == ["drunk"]
    assert entry["occurred_at"]


def test_recap_derives_penalties_from_the_recorded_stand_in_turn(
    gateway, game_session_upstream, trusted_ws_issuer, monkeypatch, live_character_sheet
) -> None:
    owner, session_id = _absent_player_with_stand_in_turn(
        gateway, game_session_upstream, trusted_ws_issuer, monkeypatch, live_character_sheet
    )
    res = gateway.get(f"/api/v1/sessions/{session_id}/absentee-recap", headers=owner)
    assert res.status_code == 200, res.text
    recap = res.json()
    assert recap["session_id"] == session_id
    assert recap["stand_in_turns"] == 1
    assert recap["penalties"] == [{"character_name": "Kyra", "penalty": "drunk"}]
    assert [a["character_name"] for a in recap["actions"]] == ["Kyra"]


def test_session_without_events_returns_empty_feed_and_empty_recap(
    gateway, game_session_upstream, trusted_ws_issuer
) -> None:
    owner = _auth(trusted_ws_issuer, "dm-evelyn")
    session_id = _owned_session(gateway, game_session_upstream, owner)

    feed = gateway.get(f"/api/v1/sessions/{session_id}/events", headers=owner)
    assert feed.status_code == 200, feed.text
    assert feed.json() == []

    recap = gateway.get(f"/api/v1/sessions/{session_id}/absentee-recap", headers=owner)
    assert recap.status_code == 200, recap.text
    assert recap.json()["stand_in_turns"] == 0
    assert recap.json()["penalties"] == []
    assert recap.json()["actions"] == []


@pytest.mark.parametrize("path", SESSION_READ_ROUTES)
def test_unknown_session_is_404_at_the_owning_service(path: str) -> None:
    client = TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )
    res = client.get(path.format(sid=uuid4()))
    assert res.status_code == 404
