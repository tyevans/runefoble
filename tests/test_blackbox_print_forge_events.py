"""Blackbox TDD test: a papercraft standee export is published as PrintPdfForged.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Setup and assertions use only the public Asset Forge standees route and the
Redis Streams entries that the route publishes.
"""

from __future__ import annotations

import pytest
from asset_forge.dependencies import set_event_bus
from asset_forge.main import app
from fastapi.testclient import TestClient
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER


def auth_headers(sub: str) -> dict[str, str]:
    """Return Bearer headers for a token that the service verifier accepts."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture(autouse=True)
def clean_environment():
    """Reset the injected event bus before and after each test."""
    set_event_bus(None)
    yield
    set_event_bus(None)


@pytest.mark.asyncio
async def test_standee_export_publishes_print_pdf_forged():
    """Exporting standees through the public route writes one PrintPdfForged entry."""
    mock_redis = MockAsyncRedis()
    set_event_bus(RedisStreamsEventBus(client=mock_redis))
    client = TestClient(app, headers=auth_headers("crafter-rowan"))

    response = client.post(
        "/api/v1/forge/standees",
        json={
            "sheet_title": "Goblin Ambush Pack",
            "standees": [{"name": "Goblin Scout", "type": "monster", "hp": 7, "color": "#e76f51"}],
            "format": "json",
        },
    )
    assert response.status_code == 200, response.text
    asset_id = response.json()["asset_id"]

    entries = [
        payload
        for _, payload in mock_redis.streams.get("runefoble.events.asset", [])
        if payload["event_type"] == "runefoble.events.asset.print_pdf_forged"
    ]
    assert len(entries) == 1
    assert asset_id in entries[0]["payload"]
    assert "standee-sheet" in entries[0]["payload"]
