"""Blackbox tests for the gateway downtime proxies (TASK-0584).

The gateway forwards stronghold, campfire, recipe combine, tavern and haggling calls to
the owning services. game_session and character_sheet run as live loopback upstreams, and
the gateway reaches them over HTTP. Setup goes through public routes only. Assertions check
owner outputs. No canned gateway payload can pass these tests.

Governed by:
- TASK-0584: Gateway Downtime Routes Proxy to Game Session and Character Sheet
- TASK-0580: Shared Typed Service Client for Gateway Proxies
- ADR-0015: no substitute values on upstream failure
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url

pytestmark = pytest.mark.usefixtures("game_session_upstream", "character_sheet_upstream")


def _headers(trusted_ws_issuer: Any, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {trusted_ws_issuer.mint(sub)}"}


@pytest.fixture
def client() -> Any:
    with TestClient(gateway_app) as test_client:
        yield test_client


def _campaign_with_session(client: TestClient, headers: dict[str, str]) -> tuple[str, str]:
    created = client.post(
        "/api/v1/campaigns",
        json={"title": f"Downtime {uuid4().hex[:8]}", "setting": "Test", "system": "5e"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]
    sessions = client.get(f"/api/v1/campaigns/{campaign_id}/sessions", headers=headers)
    assert sessions.status_code == 200, sessions.text
    return campaign_id, sessions.json()[0]["id"]


def test_stronghold_get_returns_the_owner_treasury(client: TestClient, trusted_ws_issuer) -> None:
    headers = _headers(trusted_ws_issuer, "dm_stronghold_get")
    campaign_id, _ = _campaign_with_session(client, headers)
    funded = client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/deposit",
        json={"gold": 250, "materials": {"wood": 20}},
        headers=headers,
    )
    assert funded.status_code == 200, funded.text
    upgraded = client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/upgrade",
        json={"facility_id": "watchtower", "gold_spent": 100},
        headers=headers,
    )
    assert upgraded.status_code == 200, upgraded.text

    res = client.get(f"/api/v1/campaigns/{campaign_id}/stronghold", headers=headers)

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["treasury_gold"] == 150
    assert body["facilities"]["watchtower"] == 1


def test_stronghold_upgrade_returns_the_owner_outcome(
    client: TestClient, trusted_ws_issuer
) -> None:
    headers = _headers(trusted_ws_issuer, "dm_stronghold_upgrade")
    campaign_id, _ = _campaign_with_session(client, headers)
    funded = client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/deposit",
        json={"gold": 40, "materials": {"flora": 15}},
        headers=headers,
    )
    assert funded.status_code == 200, funded.text

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/upgrade",
        json={"facility_id": "herbal_rack", "gold_spent": 40},
        headers=headers,
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["facility_id"] == "herbal_rack"
    assert body["new_tier"] == 1
    assert body["gold_spent"] == 40
    assert "status" not in body
    assert body["state"]["facilities"]["herbal_rack"] == 1


def test_stronghold_upgrade_passes_the_owner_400_through(
    client: TestClient, trusted_ws_issuer
) -> None:
    headers = _headers(trusted_ws_issuer, "dm_stronghold_bad")
    campaign_id, _ = _campaign_with_session(client, headers)

    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/upgrade",
        json={"facility_id": "moat", "gold_spent": 10},
        headers=headers,
    )

    assert res.status_code == 400
    assert "Unknown facility" in res.json()["detail"]


def test_campfire_rest_returns_the_owner_boons(client: TestClient, trusted_ws_issuer) -> None:
    headers = _headers(trusted_ws_issuer, "dm_campfire")
    campaign_id, session_id = _campaign_with_session(client, headers)

    res = client.post(
        f"/api/v1/sessions/{session_id}/rest/campfire",
        json={"rest_type": "long"},
        headers=headers,
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["session_id"] == session_id
    assert body["campaign_id"] == campaign_id
    assert "Exhaustion Cleared" in body["boons_applied"]
    assert body["status"] == "completed"


def test_campfire_rest_for_unknown_session_is_denied(client: TestClient, trusted_ws_issuer) -> None:
    """A session with no campaign link gets no participation grant, so the owner answers 403."""
    headers = _headers(trusted_ws_issuer, "dm_campfire_missing")

    res = client.post(
        f"/api/v1/sessions/session-{uuid4().hex}/rest/campfire",
        json={"rest_type": "long"},
        headers=headers,
    )

    assert res.status_code == 403


def test_combine_returns_the_character_sheet_outcome(client: TestClient, trusted_ws_issuer) -> None:
    headers = _headers(trusted_ws_issuer, "dm_combine")
    created = client.post(
        "/api/v1/characters",
        json={"name": "Bram the Tinkerer", "character_class": "Artificer", "max_hp": 24},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    character_id = created.json()["id"]

    res = client.post(
        "/api/v1/crafting/recipes/combine",
        json={
            "character_id": character_id,
            "reagents": ["Glowmoss Extract", "Volcano Ash"],
            "catalyst": "purified_water",
            "force_mishap": False,
        },
        headers=headers,
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["outcome"] in {"success", "mishap"}
    assert body["reagents_consumed"] == ["Glowmoss Extract", "Volcano Ash"]
    assert "risk_score" in body


def test_combine_for_unknown_character_passes_the_owner_denial_through(
    client: TestClient, trusted_ws_issuer
) -> None:
    """character_sheet checks  before it loads the character, so a missing one is denied."""
    headers = _headers(trusted_ws_issuer, "dm_combine_missing")

    res = client.post(
        "/api/v1/crafting/recipes/combine",
        json={"character_id": str(uuid4()), "reagents": ["Glowmoss Extract"]},
        headers=headers,
    )

    assert res.status_code == 403


def test_tavern_game_returns_the_owner_game_state(client: TestClient, trusted_ws_issuer) -> None:
    headers = _headers(trusted_ws_issuer, "dm_tavern")
    _, session_id = _campaign_with_session(client, headers)

    res = client.post(
        f"/api/v1/sessions/{session_id}/tavern/games",
        json={"game_type": "liars_dice", "wager_gold": 10, "initiator_id": "char_bram"},
        headers=headers,
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["game_id"]
    assert not body["game_id"].startswith("game-gw-")
    assert body["initiator_id"] == "char_bram"
    assert body["wager_gold"] == 10


def test_haggle_forwards_to_the_owner_negotiation(
    client: TestClient, trusted_ws_issuer, game_session_upstream: str
) -> None:
    headers = _headers(trusted_ws_issuer, "dm_haggle")
    campaign_id, session_id = _campaign_with_session(client, headers)
    with httpx.Client(base_url=game_session_upstream, timeout=10.0) as owner:
        settlement = owner.post(
            f"/api/v1/campaigns/{campaign_id}/settlements",
            json={"name": "Oakhaven", "scale": "market_town", "districts": ["artisan"]},
            headers=headers,
        )
        assert settlement.status_code == 201, settlement.text
        establishment = owner.post(
            f"/api/v1/settlements/{settlement.json()['settlement_id']}/establishments",
            json={"district_id": "artisan", "category": "commerce", "name": "The Ember Anvil"},
            headers=headers,
        )
        assert establishment.status_code == 201, establishment.text
    establishment_id = establishment.json()["establishment_id"]
    merchant_id = "npc_merchant_ember"

    res = client.post(
        f"/api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle",
        json={
            "character_id": "char_bram",
            "campaign_id": campaign_id,
            "establishment_id": establishment_id,
            "item_id": "helm_iron",
            "item_name": "Iron Helm",
            "base_price": 50,
            "offered_price": 35,
            "temperament": "stubborn_greedy",
        },
        headers=headers,
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["negotiation_id"]
    assert body["merchant_id"] == merchant_id
    assert body["establishment_id"] == establishment_id

    stored = httpx.get(
        f"{game_session_upstream}/api/v1/haggling/{body['negotiation_id']}",
        headers=headers,
        timeout=10.0,
    )
    assert stored.status_code == 200, stored.text
    assert stored.json()["establishment_id"] == establishment_id


def test_downtime_routes_answer_503_when_the_owner_is_unreachable(
    monkeypatch: pytest.MonkeyPatch, trusted_ws_issuer
) -> None:
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())
    headers = _headers(trusted_ws_issuer, "dm_offline")
    with TestClient(gateway_app) as client:
        res = client.get(f"/api/v1/campaigns/{uuid4()}/stronghold", headers=headers)

    assert res.status_code == 503
    assert res.json()["upstream"] == "game_session"
