"""Blackbox frontdoor tests for the gateway rules compendium proxy (TASK-0594).

Governing ADRs: ADR-0001 (SpiceDB Zanzibar object authorization), ADR-0014 (BDD through public
routes), ADR-0015 (the gateway forwards the caller's bearer token only).

The compendium runs as a live loopback upstream. The gateway reaches it over HTTP through
RUNEFOBLE_RULES_COMPENDIUM_URL, as it does in a cluster. Every call goes through the gateway's
public routes. The owner keeps the authorization checks. No test writes a tuple or reads private
state.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from rules_compendium.main import app as compendium_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app

HOMEBREW_PAYLOAD = {
    "rule_type": "monster",
    "title": "Abyssal Shadowstalker",
    "content": {"challenge_rating": 3.0, "creature_type": "fiend", "hit_points": 45},
}

ENCOUNTER_PAYLOAD = {"party_levels": [3, 3, 3, 3], "target_difficulty": "Medium"}


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


@pytest.fixture
def compendium_upstream(monkeypatch, trusted_ws_issuer) -> Iterator[str]:
    """Serve rules_compendium on loopback with its start-up state, and point the gateway at it."""
    with serve(compendium_app, lifespan="on") as url:
        monkeypatch.setenv("RUNEFOBLE_RULES_COMPENDIUM_URL", url)
        yield url


@pytest.fixture
def gateway(game_session_upstream, compendium_upstream) -> Iterator[TestClient]:
    """Enter the gateway lifespan after both upstreams are served and their URLs are set."""
    with TestClient(gateway_app) as client:
        yield client


def test_gateway_serves_srd_monster_stat_block(gateway, trusted_ws_issuer):
    """A verified caller reads an SRD stat block through the gateway."""
    res = gateway.get(
        "/api/v1/compendium/monsters/Goblin", headers=_auth(trusted_ws_issuer, "player_tamsin")
    )

    assert res.status_code == 200, res.text
    goblin = res.json()
    assert goblin["name"] == "Goblin"
    assert goblin["challenge_rating"] == 0.25
    assert goblin["hit_points"] == 7


def test_gateway_decodes_path_segments_for_spell_names(gateway, trusted_ws_issuer):
    """A name with a space survives the proxy: `Hold%20Person` reaches the owner as one segment."""
    res = gateway.get(
        "/api/v1/compendium/spells/Hold%20Person", headers=_auth(trusted_ws_issuer, "player_tamsin")
    )

    assert res.status_code == 200, res.text
    assert res.json()["name"] == "Hold Person"


def test_gateway_forwards_rule_search_query_string(gateway, trusted_ws_issuer):
    """The query string reaches the owner unchanged, so the owner's search returns Fireball."""
    res = gateway.get(
        "/api/v1/compendium/rules/search",
        params={"query": "fire damage explosion", "limit": "5"},
        headers=_auth(trusted_ws_issuer, "player_tamsin"),
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["query"] == "fire damage explosion"
    assert "Fireball" in [r["name"] for r in body["results"]]


def test_gateway_returns_owner_encounter_balance(gateway, trusted_ws_issuer):
    """POST encounters/balance through the gateway returns the owner's CR result."""
    res = gateway.post(
        "/api/v1/compendium/encounters/balance",
        json=ENCOUNTER_PAYLOAD,
        headers=_auth(trusted_ws_issuer, "player_tamsin"),
    )

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["party_size"] == 4
    assert data["target_difficulty"] == "Medium"


def test_homebrew_written_through_gateway_is_read_back_through_gateway(gateway, trusted_ws_issuer):
    """The campaign owner registers homebrew and lists it. Search finds it. All calls use the gateway."""
    owner = _auth(trusted_ws_issuer, "owner_orin")
    created = gateway.post("/api/v1/campaigns", json={"title": "Gateway Homebrew"}, headers=owner)
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]

    registered = gateway.post(
        "/api/v1/compendium/homebrew",
        json={"campaign_id": campaign_id, **HOMEBREW_PAYLOAD},
        headers=owner,
    )
    assert registered.status_code == 200, registered.text
    assert registered.json()["author_id"] == "owner_orin"

    listed = gateway.get(f"/api/v1/compendium/homebrew/{campaign_id}", headers=owner)
    assert listed.status_code == 200, listed.text
    assert [r["title"] for r in listed.json()] == ["Abyssal Shadowstalker"]

    found = gateway.get(
        "/api/v1/compendium/rules/search",
        params={"query": "Shadowstalker", "campaign_id": campaign_id},
        headers=owner,
    )
    assert found.status_code == 200, found.text
    assert "Abyssal Shadowstalker" in [r["name"] for r in found.json()["results"]]


def test_owner_refusal_passes_through_the_gateway(gateway, trusted_ws_issuer):
    """The owner's authorization answer reaches the caller unchanged. A stranger gets 403."""
    owner = _auth(trusted_ws_issuer, "owner_orin")
    created = gateway.post("/api/v1/campaigns", json={"title": "Refusal"}, headers=owner)
    assert created.status_code == 201, created.text

    res = gateway.post(
        "/api/v1/compendium/homebrew",
        json={"campaign_id": created.json()["id"], **HOMEBREW_PAYLOAD},
        headers=_auth(trusted_ws_issuer, "stranger_vex"),
    )

    assert res.status_code == 403, res.text


def test_anonymous_call_is_refused_by_the_gateway(gateway):
    """A call with no bearer token gets 401 at the gateway."""
    res = gateway.get("/api/v1/compendium/monsters/Goblin")

    assert res.status_code == 401, res.text


def test_owner_unreachable_returns_503_through_the_gateway(
    game_session_upstream, monkeypatch, trusted_ws_issuer
):
    """A closed port behind the gateway returns 503 that names the upstream. No substitute body."""
    monkeypatch.setenv("RUNEFOBLE_RULES_COMPENDIUM_URL", closed_port_url())
    with TestClient(gateway_app) as gateway:
        res = gateway.get(
            "/api/v1/compendium/monsters/Goblin",
            headers=_auth(trusted_ws_issuer, "player_tamsin"),
        )

    assert res.status_code == 503, res.text
    assert res.json()["upstream"] == "rules_compendium"
    assert "name" not in res.json()


def test_owner_5xx_returns_502_through_the_gateway(
    game_session_upstream, monkeypatch, trusted_ws_issuer
):
    """An owner 5xx answer becomes 502 at the gateway. The owner's body is not copied."""
    with serve(unavailable_app(503)) as down_url:
        monkeypatch.setenv("RUNEFOBLE_RULES_COMPENDIUM_URL", down_url)
        with TestClient(gateway_app) as gateway:
            res = gateway.get(
                "/api/v1/compendium/monsters/Goblin",
                headers=_auth(trusted_ws_issuer, "player_tamsin"),
            )

    assert res.status_code == 502, res.text
    assert res.json()["upstream"] == "rules_compendium"
