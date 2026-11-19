"""Blackbox tests: gateway proxies the public Watcher routes to The Watcher (TASK-0596).

The gateway verifies the caller's bearer token and forwards the request to `the_watcher`
unchanged. The Watcher runs as a live loopback upstream and owns every check (ADR-0002,
ADR-0001). The gateway keeps no Watcher state. Setup runs through public frontdoors only
(ADR-0014, Hard Invariant 7). The speak-and-act route is covered by TASK-0583 and is not listed here.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from the_watcher.main import app as watcher_app

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.ws_identity import bearer
from tests.realtime_session import open_table

DM = "dm_dora"
PLAYER = "valeros"
MISSING_FACTION = "faction-missing"

# (method, public path). Each path uses the sample values below.
WATCHER_ROUTES: tuple[tuple[str, str], ...] = (
    ("POST", "/api/v1/watcher/transcribe-and-act"),
    ("POST", "/api/v1/watcher/intent/parse"),
    ("POST", "/api/v1/watcher/intent/resolve"),
    ("POST", "/api/v1/watcher/intent/execute"),
    ("POST", "/api/v1/watcher/scenes/generate"),
    ("POST", "/api/v1/watcher/encounters/spawn"),
    ("POST", "/api/v1/watcher/encounters/npc-turn"),
    ("POST", "/api/v1/watcher/narrate"),
    ("POST", "/api/v1/watcher/stand-in/act"),
    ("POST", "/api/v1/watcher/stand-in/recap"),
    ("POST", "/api/v1/watcher/chronicle/recap"),
    ("POST", "/api/v1/watcher/actions/propose"),
    ("GET", "/api/v1/watcher/actions/pending"),
    ("POST", "/api/v1/watcher/veto"),
    ("POST", "/api/v1/watcher/approve"),
    ("POST", "/api/v1/watcher/modify"),
    ("GET", "/api/v1/watcher/whispers"),
    ("POST", "/api/v1/watcher/whispers"),
    ("POST", "/api/v1/watcher/whispers/generate"),
    ("POST", "/api/v1/watcher/whispers/{whisper_id}/dispatch"),
    ("POST", "/api/v1/campaigns/{campaign_id}/world-tick"),
    ("POST", "/api/v1/campaigns/{campaign_id}/factions"),
    ("GET", "/api/v1/campaigns/{campaign_id}/factions"),
    ("GET", "/api/v1/campaigns/{campaign_id}/factions/{faction_id}"),
    ("GET", "/api/v1/campaigns/{campaign_id}/world-ticks/latest"),
    ("POST", "/api/v1/factions/{faction_id}/resources/adjust"),
    ("POST", "/api/v1/factions/{faction_id}/bribery/resolve"),
    ("POST", "/api/v1/factions/{faction_id}/mercenaries/recruit"),
    ("GET", "/api/v1/factions/{faction_id}/resources"),
    ("POST", "/api/v1/factions/skirmish/simulate"),
    ("GET", "/api/v1/regions/{region_id}/unrest"),
)


@pytest.fixture
def watcher_url(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """Serve the real The Watcher app and point the gateway at it before the gateway starts."""
    with serve(watcher_app) as url:
        monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", url)
        yield url


@pytest.fixture
def gateway(
    watcher_url: str,
    game_session_upstream: str,
    board_state_upstream: str,
    character_sheet_upstream: str,
    voice_agent_upstream: str,
) -> Iterator[TestClient]:
    """The gateway, started after `watcher_url` is set, so its registry holds the Watcher URL."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def table(gateway: TestClient, game_session_upstream: str) -> tuple[str, str]:
    """A campaign with a DM and one player, and a session, created through public routes."""
    return open_table(gateway, game_session_upstream, DM, {PLAYER: "player"})


def _concrete(template: str, campaign_id: str, faction_id: str = MISSING_FACTION) -> str:
    return (
        template.replace("{campaign_id}", campaign_id)
        .replace("{faction_id}", faction_id)
        .replace("{region_id}", "region-north")
        .replace("{whisper_id}", "whisp-missing")
    )


def _body(method: str) -> dict[str, Any] | None:
    """An empty JSON object for a POST. The owner answers it with its own validation reply."""
    return {} if method == "POST" else None


def _send(client: Any, method: str, url: str, headers: dict[str, str]) -> httpx.Response:
    body = _body(method)
    if body is None:
        return client.request(method, url, headers=headers)
    return client.request(method, url, json=body, headers=headers)


def _faction_body(name: str) -> dict[str, Any]:
    return {"name": name, "influence": 40, "resources": 60, "disposition": "hostile"}


@pytest.mark.parametrize(("method", "template"), WATCHER_ROUTES)
def test_watcher_route_needs_a_verified_caller(
    gateway: TestClient, table: tuple[str, str], method: str, template: str
) -> None:
    """Without a bearer token the gateway answers 401 and the owner is never reached."""
    campaign_id, _ = table
    url = _concrete(template, campaign_id)

    res = _send(gateway, method, url, headers={})

    assert res.status_code == 401, res.text


@pytest.mark.parametrize(("method", "template"), WATCHER_ROUTES)
def test_watcher_route_reports_a_down_owner_as_503(
    gateway: TestClient,
    table: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    template: str,
) -> None:
    campaign_id, _ = table
    url = _concrete(template, campaign_id)
    monkeypatch.setenv("RUNEFOBLE_WATCHER_URL", closed_port_url())

    with TestClient(gateway_app) as client:
        res = _send(client, method, url, headers=bearer(DM))

    assert res.status_code == 503, res.text
    assert res.json()["upstream"] == "the_watcher"


@pytest.mark.parametrize(("method", "template"), WATCHER_ROUTES)
def test_watcher_route_answers_as_the_owner_does(
    gateway: TestClient,
    table: tuple[str, str],
    watcher_url: str,
    method: str,
    template: str,
) -> None:
    """For the same caller and body, the gateway status equals the owner status.

    An error reply carries the same JSON. A success reply is not compared, because the owner
    creates new state on each call.
    """
    campaign_id, _ = table
    url = _concrete(template, campaign_id)

    with httpx.Client(base_url=watcher_url) as owner_client:
        owner = _send(owner_client, method, url, headers=bearer(DM))
    via_gateway = _send(gateway, method, url, headers=bearer(DM))

    assert via_gateway.status_code == owner.status_code, via_gateway.text
    if owner.status_code >= 400:
        assert via_gateway.json() == owner.json()


def test_faction_registered_through_the_gateway_is_read_back_through_it(
    gateway: TestClient, table: tuple[str, str]
) -> None:
    campaign_id, _ = table
    name = f"Ashen Court {uuid4().hex[:6]}"

    created = gateway.post(
        f"/api/v1/campaigns/{campaign_id}/factions", json=_faction_body(name), headers=bearer(DM)
    )
    assert created.status_code == 200, created.text
    faction_id = created.json()["faction_id"]

    listed = gateway.get(f"/api/v1/campaigns/{campaign_id}/factions", headers=bearer(DM))
    detail = gateway.get(
        f"/api/v1/campaigns/{campaign_id}/factions/{faction_id}", headers=bearer(DM)
    )

    assert listed.status_code == 200, listed.text
    assert [f["name"] for f in listed.json()] == [name]
    assert detail.status_code == 200, detail.text
    assert detail.json()["name"] == name


def test_world_tick_through_the_gateway_returns_the_owners_bulletin(
    gateway: TestClient, table: tuple[str, str]
) -> None:
    campaign_id, _ = table
    gateway.post(
        f"/api/v1/campaigns/{campaign_id}/factions",
        json=_faction_body(f"River Guild {uuid4().hex[:6]}"),
        headers=bearer(DM),
    )

    ticked = gateway.post(
        f"/api/v1/campaigns/{campaign_id}/world-tick",
        json={"regional_stability": 40, "random_seed": 7},
        headers=bearer(DM),
    )
    latest = gateway.get(f"/api/v1/campaigns/{campaign_id}/world-ticks/latest", headers=bearer(DM))

    assert ticked.status_code == 200, ticked.text
    assert ticked.json()["campaign_id"] == campaign_id
    assert ticked.json()["intelligence_bulletin"]
    assert latest.status_code == 200, latest.text
    assert latest.json()["tick_number"] == ticked.json()["tick_number"]


def test_world_tick_without_a_body_reaches_the_owner(
    gateway: TestClient, table: tuple[str, str]
) -> None:
    """The owner takes an optional body, so the gateway forwards a request that has none."""
    campaign_id, _ = table

    res = gateway.post(f"/api/v1/campaigns/{campaign_id}/world-tick", headers=bearer(DM))

    assert res.status_code == 200, res.text
    assert res.json()["campaign_id"] == campaign_id


def test_dm_veto_through_the_gateway_removes_the_proposal(
    gateway: TestClient, table: tuple[str, str]
) -> None:
    campaign_id, session_id = table
    proposed = gateway.post(
        "/api/v1/watcher/actions/propose",
        json={
            "session_id": session_id,
            "campaign_id": campaign_id,
            "actor_name": "Valeros",
            "action_type": "attack",
            "description": "A strike at the goblin",
            "pause_window_ms": 60000,
        },
        headers=bearer(DM),
    )
    assert proposed.status_code == 200, proposed.text
    action_id = proposed.json()["action_id"]

    denied = gateway.post(
        "/api/v1/watcher/veto",
        json={"action_id": action_id, "session_id": session_id, "campaign_id": campaign_id},
        headers=bearer(PLAYER),
    )
    vetoed = gateway.post(
        "/api/v1/watcher/veto",
        json={"action_id": action_id, "session_id": session_id, "campaign_id": campaign_id},
        headers=bearer(DM),
    )
    pending = gateway.get(
        "/api/v1/watcher/actions/pending",
        params={"session_id": session_id, "campaign_id": campaign_id},
        headers=bearer(DM),
    )

    assert denied.status_code == 403, denied.text
    assert vetoed.status_code == 200, vetoed.text
    assert vetoed.json()["status"] == "vetoed"
    assert vetoed.json()["vetoed_by"] == DM
    [action] = [a for a in pending.json() if a["action_id"] == action_id]
    assert action["status"] == "vetoed"
