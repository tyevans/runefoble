"""Blackbox tests for the absentee stance saved as part of the stand-in guardrail policy (TASK-0954).

The stance is a field of the guardrail policy. The App Shell saves it through the public
`PUT /api/v1/characters/{id}/guardrails` route. The gateway forwards the body to character_sheet,
which is a live loopback upstream here. Setup uses only public routes. Governed by ADR-0015 (no
default stance) and Hard Invariant 7.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from pydantic import ValidationError
from runefoble_platform.stand_in_guardrails import StandInGuardrailPolicy

from tests.helpers.ws_identity import bearer

PLAYER = "user-sarah"


@pytest.fixture
def gateway(game_session_upstream: str, character_sheet_upstream: str) -> Iterator[TestClient]:
    with TestClient(gateway_app) as client:
        yield client


def _create_character(gateway: TestClient) -> str:
    created = gateway.post(
        "/api/v1/characters",
        json={"name": "Seoni", "characterClass": "Cleric", "maxHp": 38},
        headers=bearer(PLAYER),
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_policy_stance_defaults_to_no_stance_and_accepts_the_three_stances() -> None:
    """The policy has no stance until the player chooses one. Only three stance ids are valid."""
    assert StandInGuardrailPolicy().stance is None
    for stance in ("defensive", "cautious", "heroic"):
        assert StandInGuardrailPolicy(stance=stance).stance == stance


def test_policy_refuses_an_unknown_stance() -> None:
    with pytest.raises(ValidationError):
        StandInGuardrailPolicy(stance="reckless-bold")


def test_new_character_has_no_stance_through_the_gateway(gateway: TestClient) -> None:
    char_id = _create_character(gateway)
    read = gateway.get(f"/api/v1/characters/{char_id}/guardrails", headers=bearer(PLAYER))
    assert read.status_code == 200, read.text
    assert read.json()["stance"] is None


def test_chosen_stance_is_saved_and_read_back_through_the_gateway(gateway: TestClient) -> None:
    char_id = _create_character(gateway)
    saved = gateway.put(
        f"/api/v1/characters/{char_id}/guardrails",
        json={"stance": "cautious", "protect_allies": ["Marcus"], "avoid_melee": True},
        headers=bearer(PLAYER),
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["stand_in_guardrails"]["stance"] == "cautious"

    read = gateway.get(f"/api/v1/characters/{char_id}/guardrails", headers=bearer(PLAYER))
    assert read.status_code == 200, read.text
    assert read.json()["stance"] == "cautious"
    assert read.json()["protect_allies"] == ["Marcus"]


def test_unknown_stance_is_refused_with_422_through_the_gateway(gateway: TestClient) -> None:
    char_id = _create_character(gateway)
    res = gateway.put(
        f"/api/v1/characters/{char_id}/guardrails",
        json={"stance": "reckless"},
        headers=bearer(PLAYER),
    )
    assert res.status_code == 422, res.text
    read = gateway.get(f"/api/v1/characters/{char_id}/guardrails", headers=bearer(PLAYER))
    assert read.json()["stance"] is None
