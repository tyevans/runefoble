"""Blackbox tests for TASK-0572: Campaign Lore events published through the repository.

Governed by:
- ADR-0011: state transitions are events saved through AggregateRepository
- ADR-0006: Redis Streams event streaming
- Hard Invariant 7: blackbox TDD with frontdoor setup

Setup and actions use only public Campaign Lore HTTP routes. Assertions read the Redis
Stream that the repository publishes to, through the Redis double at the process boundary.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from campaign_lore.main import app
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import bearer

DOCUMENT_INGESTED_STREAM = "runefoble.events.lore.document_ingested"
CODEX_ENTRY_PUBLISHED_STREAM = "runefoble.events.lore.codex_entry_published"
VISITOR_SUBJECT = "lore-test-visitor"

pytestmark = pytest.mark.usefixtures("lore_backends")


def _payloads(mock_redis: MockAsyncRedis, stream: str) -> list[dict]:
    """Return the decoded payload of every entry on one stream."""
    return [
        json.loads(fields["payload"]) for _entry_id, fields in mock_redis.streams.get(stream, [])
    ]


@pytest.mark.asyncio
async def test_ingested_document_is_published_once_to_lore_stream(mock_bus: MockAsyncRedis) -> None:
    """Ingesting a document through the public route publishes one document_ingested entry."""
    campaign_id = str(uuid4())
    dm = f"dm-{uuid4().hex[:8]}"
    await get_spicedb_client().write_relationship(
        "campaign", campaign_id, "dungeon_master", "user", dm
    )
    with TestClient(app, headers=bearer(VISITOR_SUBJECT)) as client:
        ingested = client.post(
            "/api/v1/lore/documents",
            json={
                "campaign_id": campaign_id,
                "title": "The Knights of the Silver Dawn",
                "content": "Sir Gareth guards the Citadel of Light in Neverwinter.",
            },
            headers=bearer(dm),
        )
    assert ingested.status_code == 200, ingested.text
    document_id = ingested.json()["document_id"]

    entries = _payloads(mock_bus, DOCUMENT_INGESTED_STREAM)
    assert [entry["document_id"] for entry in entries] == [document_id]


@pytest.mark.asyncio
async def test_published_codex_entry_is_published_once_to_lore_stream(
    mock_bus: MockAsyncRedis,
) -> None:
    """Publishing a codex entry through the public route publishes one entry to its stream."""
    campaign_id = str(uuid4())
    author = f"author-{uuid4().hex[:8]}"
    await get_spicedb_client().write_relationship("campaign", campaign_id, "player", "user", author)
    with TestClient(app, headers=bearer(VISITOR_SUBJECT)) as client:
        published = client.post(
            f"/api/v1/campaigns/{campaign_id}/codex/entries",
            json={
                "title": "Field Notes",
                "content": "The fen smells of iron.",
                "privacy": "private",
            },
            headers=bearer(author),
        )
    assert published.status_code == 201, published.text
    entry_id = published.json()["entry_id"]

    entries = _payloads(mock_bus, CODEX_ENTRY_PUBLISHED_STREAM)
    assert [entry["entry_id"] for entry in entries] == [entry_id]
