"""Blackbox tests: repositories resolve the event store through the provider per operation.

Governed by ADR-0011, ADR-0015 and Hard Invariant 7 (TASK-0773). Setup goes through the public
character routes. The store is replaced only through the provider seam (`set_event_store`).
Repositories are created at import time, so a swap must reach them without a restart.
"""

from __future__ import annotations

from character_sheet.main import app as character_app
from fastapi.testclient import TestClient
from runefoble_platform.event_sourcing import InMemoryEventStore, set_event_store

from tests.helpers.event_store_seam import store_outage
from tests.helpers.ws_identity import SIGNING_ISSUER


def _client() -> TestClient:
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('character-owner')}"}
    return TestClient(character_app, headers=headers)


def _create_character(client: TestClient) -> str:
    res = client.post(
        "/api/v1/characters",
        json={"name": "Apprentice", "character_class": "Wizard", "max_hp": 16},
    )
    assert res.status_code == 200, res.text
    return str(res.json()["character_id"])


def test_route_read_follows_the_store_installed_through_the_provider() -> None:
    """A route that reads during a store outage answers 503. It does not read a stale store."""
    client = _client()
    char_id = _create_character(client)

    with store_outage():
        outage = client.get(f"/api/v1/characters/{char_id}")
    assert outage.status_code == 503, outage.text

    after = client.get(f"/api/v1/characters/{char_id}")
    assert after.status_code == 200, after.text
    assert after.json()["name"] == "Apprentice"


def test_route_writes_and_reads_the_store_installed_through_the_provider() -> None:
    """Characters written to a newly installed store are read back from that same store."""
    client = _client()
    installed = InMemoryEventStore()
    set_event_store(installed)
    try:
        char_id = _create_character(client)
        read_back = client.get(f"/api/v1/characters/{char_id}")
        assert read_back.status_code == 200, read_back.text
        assert read_back.json()["name"] == "Apprentice"
    finally:
        set_event_store(None)
