"""Blackbox TDD tests for the character health stream (TASK-0574).

A health change publishes CharacterHealthChanged to the character stream. The event carries the
session the change happened in and the character's campaign. A change with no session carries
an explicit null session id.

Governed by Hard Invariant 2 (events are the record), Hard Invariant 7 (setup and assertions go
through public HTTP frontdoors and the published stream), and ADR-0015 (services verify tokens).
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest
from character_sheet.main import app
from fastapi.testclient import TestClient

from tests.helpers.ws_identity import SIGNING_ISSUER

CHARACTER_STREAM = "runefoble.events.character"


def _client() -> TestClient:
    headers = {"Authorization": f"Bearer {SIGNING_ISSUER.mint('character-owner')}"}
    return TestClient(app, headers=headers)


async def _health_events(bus: Any, character_id: str) -> list[dict[str, Any]]:
    """Return the CharacterHealthChanged payloads published for one character."""
    client = await bus.get_client()
    entries = client.streams.get(CHARACTER_STREAM, [])
    payloads = []
    for _entry_id, fields in entries:
        if fields.get("event_type") != "CharacterHealthChanged":
            continue
        payload = json.loads(fields["payload"])
        if str(payload.get("aggregate_id")) == character_id:
            payloads.append(payload)
    return payloads


def _create_fighter(client: TestClient) -> str:
    res = client.post(
        "/api/v1/characters",
        json={"name": "Valeros", "character_class": "Fighter", "max_hp": 30},
    )
    assert res.status_code == 200, res.text
    return res.json()["character_id"]


@pytest.mark.asyncio
async def test_health_change_in_a_session_publishes_the_session_id(default_redis_event_bus):
    """A damage request that names a session publishes that session on the health event."""
    client = _client()
    char_id = _create_fighter(client)
    session_id = str(uuid4())

    res = client.post(
        f"/api/v1/characters/{char_id}/health",
        json={"delta": -7, "source": "Goblin Arrow", "session_id": session_id},
    )

    assert res.status_code == 200, res.text
    published = await _health_events(default_redis_event_bus, char_id)
    assert len(published) == 1
    assert published[0]["session_id"] == session_id
    assert published[0]["delta"] == -7
    assert published[0]["current_hp"] == 23


@pytest.mark.asyncio
async def test_health_change_without_a_session_publishes_an_explicit_null(default_redis_event_bus):
    """A health change with no session names no session. The field is null, not the character id."""
    client = _client()
    char_id = _create_fighter(client)

    res = client.post(f"/api/v1/characters/{char_id}/health", json={"delta": -4})

    assert res.status_code == 200, res.text
    published = await _health_events(default_redis_event_bus, char_id)
    assert len(published) == 1
    assert published[0]["session_id"] is None
    assert published[0]["campaign_id"] is None
