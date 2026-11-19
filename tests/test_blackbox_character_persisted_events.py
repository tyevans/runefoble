"""Blackbox TDD tests for persisted spell unprepare and stand-in activation (TASK-0570).

Governed by Hard Invariant 2 (state changes flow through event-sourced aggregates) and
Hard Invariant 7 (all setup and assertions go through public HTTP frontdoors).

A service restart is simulated by building a new AggregateRepository over the same durable
event store and routing the next HTTP requests through it. Nothing reads or writes private
aggregate state.
"""

from collections.abc import Iterator

import pytest
from character_sheet import dependencies as deps
from character_sheet.aggregate import CharacterAggregate
from character_sheet.main import app
from eventsource.domain.event_registry import get_event_class_or_none
from fastapi.testclient import TestClient
from runefoble_events.events import SpellUnprepared, StandInActivated, StandInReleased
from runefoble_platform.event_sourcing import InMemoryEventStore, create_aggregate_repository

from tests.helpers.ws_identity import bearer


@pytest.fixture
def durable_store() -> InMemoryEventStore:
    """One event store shared by every service instance in a test (the durable tier)."""
    return InMemoryEventStore()


@pytest.fixture
def restart(durable_store: InMemoryEventStore) -> Iterator[object]:
    """Return a function that starts a fresh service instance over the same event store."""

    def _start() -> TestClient:
        instance_repo = create_aggregate_repository(CharacterAggregate, event_store=durable_store)
        app.dependency_overrides[deps.get_repository] = lambda: instance_repo
        return TestClient(app, headers=bearer("character-owner"))

    yield _start
    app.dependency_overrides.pop(deps.get_repository, None)


def _create_cleric(client: TestClient, name: str) -> str:
    res = client.post(
        "/api/v1/characters",
        json={"name": name, "character_class": "Cleric", "max_hp": 10},
    )
    assert res.status_code == 200, res.text
    return res.json()["character_id"]


def test_unprepared_spell_stays_unprepared_after_restart(restart):
    """Prepare then unprepare a spell; after restart the spell is absent from the sheet."""
    client = restart()
    char_id = _create_cleric(client, "Unprepare Tester")
    prep = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Shield", "spell_level": 1},
    )
    assert prep.status_code == 200, prep.text
    assert "Shield" in prep.json()["prepared_spells"]

    unprep = client.post(
        f"/api/v1/characters/{char_id}/spells/prepare",
        json={"spell_name": "Shield", "is_prepared": False},
    )
    assert unprep.status_code == 200, unprep.text
    assert "Shield" not in unprep.json()["prepared_spells"]

    reloaded = restart().get(f"/api/v1/characters/{char_id}")
    assert reloaded.status_code == 200, reloaded.text
    assert "Shield" not in reloaded.json()["prepared_spells"]


def test_stand_in_activation_survives_restart_and_applies_permadeath_lock(restart):
    """Activate the stand-in through the route; after restart, lethal damage stabilizes at 0 HP."""
    client = restart()
    char_id = _create_cleric(client, "Stand-In Tester")
    activate = client.post(
        f"/api/v1/characters/{char_id}/stand-in",
        json={"active": True, "session_id": "session-restart"},
    )
    assert activate.status_code == 200, activate.text
    assert activate.json()["is_stand_in_active"] is True

    after_restart = restart()
    state = after_restart.get(f"/api/v1/characters/{char_id}")
    assert state.status_code == 200, state.text
    assert state.json()["is_stand_in_active"] is True

    hit = after_restart.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -50, "source": "Dragon Breath"},
    )
    assert hit.status_code == 200, hit.text
    body = hit.json()
    assert body["current_hp"] == 0
    assert "unconscious_stabilized" in body["conditions"]


def test_stand_in_release_removes_permadeath_lock_after_restart(restart):
    """Activate then release the stand-in; after restart, lethal damage is not stabilized."""
    client = restart()
    char_id = _create_cleric(client, "Release Tester")
    client.post(f"/api/v1/characters/{char_id}/stand-in", json={"active": True})
    release = client.post(f"/api/v1/characters/{char_id}/stand-in", json={"active": False})
    assert release.status_code == 200, release.text
    assert release.json()["is_stand_in_active"] is False

    after_restart = restart()
    hit = after_restart.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -50, "source": "Dragon Breath"},
    )
    assert hit.status_code == 200, hit.text
    assert "unconscious_stabilized" not in hit.json()["conditions"]


def test_unprepare_and_stand_in_events_are_registered():
    """SpellUnprepared, StandInActivated, and StandInReleased are registered event types."""
    assert get_event_class_or_none("runefoble.events.character.spell_unprepared") is SpellUnprepared
    assert (
        get_event_class_or_none("runefoble.events.character.stand_in_activated") is StandInActivated
    )
    assert (
        get_event_class_or_none("runefoble.events.character.stand_in_released") is StandInReleased
    )
