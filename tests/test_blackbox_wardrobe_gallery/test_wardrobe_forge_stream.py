"""Blackbox TDD test: a forged wardrobe variant reaches the character event stream.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Setup and assertions use only the public Asset Forge HTTP route and the
Redis Streams entries that the route publishes.
"""

from __future__ import annotations

import pytest
from asset_forge.dependencies import set_event_bus as set_forge_bus
from fastapi.testclient import TestClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis


@pytest.mark.asyncio
async def test_forged_wardrobe_variant_publishes_to_character_stream(forge_client: TestClient):
    """A wardrobe variant forged through the public route lands on runefoble.events.character."""
    mock_redis = MockAsyncRedis()
    set_forge_bus(RedisStreamsEventBus(client=mock_redis))

    response = forge_client.post(
        "/api/v1/forge/wardrobe",
        json={
            "character_id": "00000000-0000-0000-0000-000000000042",
            "character_name": "Nadia",
            "attire_type": "arctic_tundra",
        },
    )
    assert response.status_code == 200, response.text
    variant_id = response.json()["variant_id"]

    character_entries = mock_redis.streams.get("runefoble.events.character", [])
    variant_entries = [
        payload
        for _, payload in character_entries
        if payload["event_type"] == "runefoble.events.character.portrait_variant_generated"
    ]
    assert len(variant_entries) == 1
    assert variant_id in variant_entries[0]["payload"]

    assert not any(
        payload["event_type"] == "runefoble.events.character.portrait_variant_generated"
        for _, payload in mock_redis.streams.get("runefoble.events.asset", [])
    )
