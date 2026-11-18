"""Blackbox frontdoor tests: a character write during an event store outage answers 503.

A store outage is a server fault. Write routes must answer 503, publish no event, and leave the
character unchanged. A bad request must still answer 400 or 422.

Governed by ADR-0011, ADR-0014, Hard Invariant 7 and TASK-0781.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

import pytest
from character_sheet.main import app as character_app
from fastapi.testclient import TestClient

from tests.helpers.event_store_seam import store_outage
from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def char_client() -> TestClient:
    return TestClient(character_app, headers=auth_headers("character-owner"))


def _create_character(client: TestClient) -> str:
    res = client.post(
        "/api/v1/characters",
        json={"name": f"Outage Hero {uuid4()}", "character_class": "Fighter", "max_hp": 20},
    )
    assert res.status_code == 200, res.text
    return res.json()["character_id"]


def _published_count(bus: MockAsyncRedis) -> int:
    return sum(len(entries) for entries in bus.streams.values())


def _outage_writes(char_id: str) -> list[tuple[str, Callable[[TestClient], object]]]:
    """Each write route that persists a character, with a valid body. Named for failure reports."""
    base = f"/api/v1/characters/{char_id}"
    return [
        ("health", lambda c: c.post(f"{base}/health", json={"delta": -5, "source": "damage"})),
        (
            "guardrails",
            lambda c: c.put(f"{base}/guardrails", json={"risk_threshold": "balanced"}),
        ),
        (
            "stand-in",
            lambda c: c.post(f"{base}/stand-in", json={"active": True, "session_id": "s-1"}),
        ),
        (
            "penalty",
            lambda c: c.post(
                f"{base}/penalties",
                json={"penalty_type": "drunk", "description": "Late to game night"},
            ),
        ),
        (
            "condition",
            lambda c: c.post(f"{base}/conditions", json={"condition": "blinded"}),
        ),
        (
            "inventory",
            lambda c: c.post(f"{base}/inventory", json={"item_id": "rope-1", "name": "Rope"}),
        ),
        (
            "equipment",
            lambda c: c.post(
                f"{base}/equipment", json={"slot": "main_hand", "item_name": "Longsword"}
            ),
        ),
    ]


def test_write_routes_answer_503_during_store_outage_and_persist_nothing(
    char_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    """Every write route answers 503 during an outage, publishes no event, and changes no state."""
    char_id = _create_character(char_client)
    before_state = char_client.get(f"/api/v1/characters/{char_id}").json()
    published_before = _published_count(mock_bus)

    for route_name, send in _outage_writes(char_id):
        with store_outage():
            res = send(char_client)
        assert res.status_code == 503, f"{route_name}: {res.status_code} {res.text}"

    assert _published_count(mock_bus) == published_before
    assert char_client.get(f"/api/v1/characters/{char_id}").json() == before_state


def test_campaign_assignment_answers_503_during_store_outage(
    char_client: TestClient, mock_bus: MockAsyncRedis
) -> None:
    """A campaign assignment during an outage answers 503 and publishes no event."""
    char_id = _create_character(char_client)
    published_before = _published_count(mock_bus)

    with store_outage():
        res = char_client.patch(
            f"/api/v1/characters/{char_id}/campaign",
            json={"campaign_id": "camp-outage"},
        )

    assert res.status_code == 503, res.text
    assert _published_count(mock_bus) == published_before


def test_bad_requests_still_answer_400_and_422(char_client: TestClient) -> None:
    """Domain validation still answers 400, and a malformed body still answers 422."""
    char_id = _create_character(char_client)
    base = f"/api/v1/characters/{char_id}"

    clear_unknown = char_client.delete(f"{base}/penalties/drunk")
    assert clear_unknown.status_code == 400, clear_unknown.text

    remove_unknown = char_client.delete(f"{base}/conditions/blinded")
    assert remove_unknown.status_code == 400, remove_unknown.text

    malformed = char_client.post(f"{base}/health", json={"delta": "lots"})
    assert malformed.status_code == 422, malformed.text
