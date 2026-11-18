"""Blackbox tests for the gateway shared-world caravan proxy (TASK-0807).

The gateway forwards the caravan contract routes to game_session. It holds no contract
state. The owner decides every permission and every status. A stranger gets the owner's 403.
An unreachable owner returns 503. An owner 5xx returns 502. The owner runs as a live
loopback upstream (ADR-0014, ADR-0015). Setup goes through public routes only.

Governed by:
- TASK-0807: Gateway Proxies Shared-World Caravan Routes
- ADR-0015 (b): the gateway is thin and returns no substitute values
- Hard Invariant 7: Blackbox TDD with public frontdoors
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app

from tests.helpers.live_services import closed_port_url, serve, unavailable_app
from tests.helpers.ws_identity import SIGNING_ISSUER

OFFICER = "guild_officer_marrow"
CONTRACTOR = "captain_val"
STRANGER = "stranger_nobody"

CONTRACT_BODY = {
    "origin_outpost": "Oakhaven",
    "destination_outpost": "Ironford",
    "cargo": {"medicinal_herbs": 40, "refined_iron": 20},
    "cargo_value": 600,
    "route_risk_level": "medium",
    "transit_stages": 1,
    "escort_collateral": 100,
    "reward_gold": 300,
    "reward_reputation": 20,
    "posted_by_campaign_id": str(uuid4()),
}


def _bearer(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(user_id)}"}


@pytest.fixture
def gateway_client(trusted_ws_issuer, game_session_upstream) -> Iterator[TestClient]:
    """The gateway lifespan starts after game_session_upstream sets the owner URL."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def shared_world(game_session_upstream: str) -> str:
    """The officer creates a shared world through the owner's public route."""
    with httpx.Client(base_url=game_session_upstream, timeout=10.0) as owner:
        created = owner.post(
            "/api/v1/shared-worlds", json={"name": "Ashen Frontier"}, headers=_bearer(OFFICER)
        )
    assert created.status_code == 201, created.text
    return created.json()["shared_world_id"]


def _contracts_url(world_id: str) -> str:
    return f"/api/v1/shared-worlds/{world_id}/caravans/contracts"


def _post_contract(client: TestClient, world_id: str) -> str:
    res = client.post(_contracts_url(world_id), json=CONTRACT_BODY, headers=_bearer(OFFICER))
    assert res.status_code == 201, res.text
    return res.json()["contract"]["contract_id"]


def test_create_shared_world_then_post_contract_through_gateway(
    gateway_client: TestClient, game_session_upstream: str
) -> None:
    """The officer founds a shared world through the gateway. The owner records the officer as guild officer."""
    res = gateway_client.post(
        "/api/v1/shared-worlds", json={"name": "Gate Frontier"}, headers=_bearer(OFFICER)
    )

    assert res.status_code == 201, res.text
    world_id = res.json()["shared_world_id"]
    listed = gateway_client.post(
        _contracts_url(world_id), json=CONTRACT_BODY, headers=_bearer(OFFICER)
    )
    assert listed.status_code == 201, listed.text


def test_post_contract_returns_the_owner_status_and_body(
    gateway_client: TestClient, shared_world: str
) -> None:
    res = gateway_client.post(
        _contracts_url(shared_world), json=CONTRACT_BODY, headers=_bearer(OFFICER)
    )

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["shared_world_id"] == shared_world
    assert body["contract"]["status"] == "open"
    assert body["contract"]["origin_outpost"] == "Oakhaven"


def test_list_contracts_applies_the_owner_filters(
    gateway_client: TestClient, shared_world: str
) -> None:
    contract_id = _post_contract(gateway_client, shared_world)

    listed = gateway_client.get(_contracts_url(shared_world), headers=_bearer(OFFICER))
    assert listed.status_code == 200, listed.text
    assert [c["contract_id"] for c in listed.json()["contracts"]] == [contract_id]

    filtered = gateway_client.get(
        _contracts_url(shared_world),
        params={"risk_level": "deadly"},
        headers=_bearer(OFFICER),
    )
    assert filtered.status_code == 200, filtered.text
    assert filtered.json()["contracts"] == []


def test_get_contract_returns_the_owner_body(gateway_client: TestClient, shared_world: str) -> None:
    contract_id = _post_contract(gateway_client, shared_world)

    res = gateway_client.get(
        f"{_contracts_url(shared_world)}/{contract_id}", headers=_bearer(OFFICER)
    )

    assert res.status_code == 200, res.text
    assert res.json()["contract"]["contract_id"] == contract_id


def test_accept_dispatch_and_fulfill_follow_the_owner_lifecycle(
    gateway_client: TestClient, shared_world: str
) -> None:
    contract_id = _post_contract(gateway_client, shared_world)
    action_url = f"{_contracts_url(shared_world)}/{contract_id}"

    accepted = gateway_client.post(
        f"{action_url}/accept",
        json={"contractor_campaign_id": str(uuid4()), "contractor_party_name": "Val's Freeblades"},
        headers=_bearer(OFFICER),
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["contract"]["status"] == "accepted"

    dispatched = gateway_client.post(
        f"{action_url}/dispatch",
        json={"dispatched_by_campaign_id": str(uuid4())},
        headers=_bearer(OFFICER),
    )
    assert dispatched.status_code == 200, dispatched.text
    assert dispatched.json()["status"] == "in_transit"

    fulfilled = gateway_client.post(f"{action_url}/fulfill", json={}, headers=_bearer(OFFICER))
    assert fulfilled.status_code == 200, fulfilled.text
    assert fulfilled.json()["contract"]["status"] == "fulfilled"
    assert fulfilled.json()["payout"]["status"] == "fulfilled"


def test_ambush_report_returns_the_owner_body(
    gateway_client: TestClient, shared_world: str
) -> None:
    contract_id = _post_contract(gateway_client, shared_world)
    action_url = f"{_contracts_url(shared_world)}/{contract_id}"
    gateway_client.post(
        f"{action_url}/accept",
        json={"contractor_campaign_id": str(uuid4()), "contractor_party_name": "Val's Freeblades"},
        headers=_bearer(OFFICER),
    )
    gateway_client.post(
        f"{action_url}/dispatch",
        json={"dispatched_by_campaign_id": str(uuid4())},
        headers=_bearer(OFFICER),
    )

    res = gateway_client.post(
        f"{action_url}/ambush",
        json={
            "stage_index": 1,
            "ambush_type": "goblin_archers",
            "danger_level": 2,
            "outcome": "repelled",
            "cargo_loss_percentage": 0.0,
            "reported_by_campaign_id": str(uuid4()),
            "notes": "Ambush defeated.",
        },
        headers=_bearer(OFFICER),
    )

    assert res.status_code == 200, res.text
    assert res.json()["ambush"]["outcome"] == "repelled"


def test_stranger_gets_the_owner_403(gateway_client: TestClient, shared_world: str) -> None:
    contract_id = _post_contract(gateway_client, shared_world)

    listed = gateway_client.get(_contracts_url(shared_world), headers=_bearer(STRANGER))
    assert listed.status_code == 403, listed.text
    assert "Permission denied" in listed.json()["detail"]

    accepted = gateway_client.post(
        f"{_contracts_url(shared_world)}/{contract_id}/accept",
        json={"contractor_campaign_id": str(uuid4()), "contractor_party_name": "Stray Blades"},
        headers=_bearer(STRANGER),
    )
    assert accepted.status_code == 403, accepted.text


def test_missing_bearer_token_returns_401(gateway_client: TestClient, shared_world: str) -> None:
    res = gateway_client.get(_contracts_url(shared_world))

    assert res.status_code == 401


def test_unreachable_owner_returns_503(trusted_ws_issuer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        res = client.get(_contracts_url(str(uuid4())), headers=_bearer(OFFICER))

    assert res.status_code == 503
    assert "upstream" in res.text


def test_owner_5xx_returns_502_without_a_substitute_body(
    trusted_ws_issuer, monkeypatch: pytest.MonkeyPatch
) -> None:
    with serve(unavailable_app(503)) as owner_url:
        monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", owner_url)
        with TestClient(gateway_app) as client:
            res = client.post(
                _contracts_url(str(uuid4())), json=CONTRACT_BODY, headers=_bearer(OFFICER)
            )

    assert res.status_code == 502
    assert "contracts" not in res.json()


def test_empty_owner_url_returns_503(trusted_ws_issuer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", "")
    with TestClient(gateway_app) as client:
        res = client.get(_contracts_url(str(uuid4())), headers=_bearer(OFFICER))

    assert res.status_code == 503
