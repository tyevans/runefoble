"""Frontdoor blackbox tests for merchant creation and the haggle application service.

Part of TASK-0728 / PRD-0024 / US-0047 / US-0075.
Governed by ADR-0011, ADR-0015 (c, f), and Hard Invariant 7.

Store outages are injected at the repository seam that the routes read through
(`get_merchant_repository`, `get_tavern_repository`). The routes see only a failing load.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session import dependencies
from game_session.main import app as session_app
from game_session.shared.streams import STREAM_TAVERN

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.module_state import SeamRestorer
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")

STUBBORN_NAME = "Thorin Stoneforged (Dwarven Blacksmith)"


class UnavailableRepository:
    """A repository whose store cannot be reached. Every load fails. Saves are recorded."""

    def __init__(self) -> None:
        self.saved: list[Any] = []

    async def load(self, _aggregate_id: Any) -> Any:
        raise ConnectionError("event store unreachable")

    async def save(self, aggregate: Any) -> None:
        self.saved.append(aggregate)


@pytest.fixture
def client() -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


def _owned_session(client: TestClient) -> str:
    """Create a campaign and one of its sessions through public routes. The caller owns both."""
    campaign = client.post("/api/v1/campaigns", json={"title": "Merchant Campaign"})
    assert campaign.status_code == 201, campaign.text
    session = client.post(
        f"/api/v1/campaigns/{campaign.json()['id']}/sessions", json={"title": "Market Day"}
    )
    assert session.status_code == 201, session.text
    return session.json()["id"]


def _haggle(client: TestClient, session_id: str, merchant_id: str, offered: int) -> Any:
    return client.post(
        f"/api/v1/sessions/{session_id}/merchants/{merchant_id}/haggle",
        params={"temperament": "stubborn_greedy"},
        json={
            "character_id": "char_bram",
            "item_name": "Reinforced Shield",
            "base_price": 50,
            "offered_price": offered,
            "charisma_modifier": 3,
        },
    )


def _event_types(mock_bus: MockAsyncRedis) -> list[str]:
    entries = mock_bus.streams.get(STREAM_TAVERN, [])
    return [entry[1].get("event_type", "") for entry in entries]


def test_unknown_merchant_returns_not_found(client: TestClient) -> None:
    res = client.get(f"/api/v1/merchants/merchant_never_seen_{uuid4().hex[:8]}")
    assert res.status_code == 404, res.text


def test_haggle_on_new_merchant_creates_merchant_before_negotiating(
    client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    session_id = _owned_session(client)
    merchant_id = f"merchant_new_{uuid4().hex[:8]}"

    res = _haggle(client, session_id, merchant_id, offered=35)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["merchant_id"] == merchant_id
    assert body["temperament"] == "stubborn_greedy"
    assert body["outcome"] == "countered"

    types = _event_types(mock_bus)
    assert "runefoble.events.tavern.merchant_created" in types
    assert "runefoble.events.tavern.haggling_negotiated" in types
    assert types.index("runefoble.events.tavern.merchant_created") < types.index(
        "runefoble.events.tavern.haggling_negotiated"
    )

    profile = client.get(f"/api/v1/merchants/{merchant_id}")
    assert profile.status_code == 200, profile.text
    profile_body = profile.json()
    assert profile_body["merchant_id"] == merchant_id
    assert profile_body["name"] == STUBBORN_NAME
    assert profile_body["temperament"] == "stubborn_greedy"
    assert profile_body["total_negotiations"] == 1


def test_haggle_on_existing_merchant_does_not_create_it_again(
    client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    session_id = _owned_session(client)
    merchant_id = f"merchant_repeat_{uuid4().hex[:8]}"

    assert _haggle(client, session_id, merchant_id, offered=35).status_code == 200
    second = _haggle(client, session_id, merchant_id, offered=40)
    assert second.status_code == 200, second.text

    types = _event_types(mock_bus)
    assert types.count("runefoble.events.tavern.merchant_created") == 1
    assert types.count("runefoble.events.tavern.haggling_negotiated") == 2

    profile = client.get(f"/api/v1/merchants/{merchant_id}").json()
    assert profile["total_negotiations"] == 2


def test_merchant_profile_store_outage_returns_unavailable(
    client: TestClient, seam_restorer: SeamRestorer
) -> None:
    seam_restorer.replace(
        dependencies.merchant_repository.get,
        dependencies.merchant_repository.set,
        UnavailableRepository(),
    )

    res = client.get("/api/v1/merchants/merchant_any")
    assert res.status_code == 503, res.text


def test_haggle_store_outage_returns_unavailable_and_saves_nothing(
    client: TestClient, mock_bus: MockAsyncRedis, seam_restorer: SeamRestorer
) -> None:
    session_id = _owned_session(client)
    repo = UnavailableRepository()
    seam_restorer.replace(
        dependencies.merchant_repository.get, dependencies.merchant_repository.set, repo
    )
    events_before = len(_event_types(mock_bus))

    res = _haggle(client, session_id, "merchant_outage", offered=35)
    assert res.status_code == 503, res.text
    assert repo.saved == []
    assert len(_event_types(mock_bus)) == events_before


def test_minigame_store_outage_returns_unavailable(
    client: TestClient, seam_restorer: SeamRestorer
) -> None:
    session_id = _owned_session(client)
    seam_restorer.replace(
        dependencies.tavern_repository.get,
        dependencies.tavern_repository.set,
        UnavailableRepository(),
    )

    res = client.get(f"/api/v1/sessions/{session_id}/tavern/games/game-missing1")
    assert res.status_code == 503, res.text


def test_unknown_minigame_returns_not_found(client: TestClient) -> None:
    session_id = _owned_session(client)

    res = client.get(f"/api/v1/sessions/{session_id}/tavern/games/game-missing2")
    assert res.status_code == 404, res.text
