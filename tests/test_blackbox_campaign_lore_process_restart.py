"""Blackbox durability tests for Campaign Lore across a process restart (TASK-0572).

Governed by:
- ADR-0011: the event store is the source of truth; read models are rebuilt from events
- ADR-0015 (a) and (f): no in-process state holds domain facts
- Hard Invariant 7: blackbox TDD with frontdoor setup

A restart is a fresh Campaign Lore process. The test removes every `campaign_lore` module
from `sys.modules` and imports the service again, so the new process has no module-level
state. The event store, the Redis double, and SpiceDB are shared, as they are in production.
Setup and assertions use only public HTTP routes.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from uuid import uuid4

import pytest
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER, bearer

pytestmark = pytest.mark.usefixtures("lore_backends", "reset_event_store")

DM_SUBJECT = f"dm-{uuid4().hex[:8]}"
PLAYER_SUBJECT = f"player-{uuid4().hex[:8]}"


def _is_campaign_lore(name: str) -> bool:
    return name == "campaign_lore" or name.startswith("campaign_lore.")


@pytest.fixture
def isolated_campaign_lore_modules() -> Iterator[None]:
    """Restore the original Campaign Lore modules after each test."""
    saved = {name: mod for name, mod in sys.modules.items() if _is_campaign_lore(name)}
    yield
    for name in [n for n in sys.modules if _is_campaign_lore(n)]:
        del sys.modules[name]
    sys.modules.update(saved)


@pytest.fixture
def redis_double() -> MockAsyncRedis:
    return MockAsyncRedis()


def _boot_lore_process(redis: MockAsyncRedis):
    """Start a new Campaign Lore process over the shared event store and Redis double."""
    for name in [n for n in sys.modules if _is_campaign_lore(n)]:
        del sys.modules[name]
    main = importlib.import_module("campaign_lore.main")
    deps = importlib.import_module("campaign_lore.dependencies")
    identity = importlib.import_module("campaign_lore.identity")
    identity.set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    deps.set_event_bus(RedisStreamsEventBus(client=redis))
    return main.app


async def _seed_campaign(campaign_id: str) -> None:
    """Make the DM run the campaign and the player a member. Lore has no membership route."""
    spicedb = get_spicedb_client()
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", DM_SUBJECT)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", PLAYER_SUBJECT)


@pytest.mark.asyncio
async def test_codex_entry_is_listed_after_process_restart(
    isolated_campaign_lore_modules: None, redis_double: MockAsyncRedis
) -> None:
    """A codex entry published before a restart still appears in the campaign codex list."""
    from fastapi.testclient import TestClient

    campaign_id = str(uuid4())
    await _seed_campaign(campaign_id)

    app = _boot_lore_process(redis_double)
    with TestClient(app) as first:
        published = first.post(
            f"/api/v1/campaigns/{campaign_id}/codex/entries",
            json={
                "title": "The Sunken Tower",
                "content": "The tower lies beneath the Whispering Fen.",
                "privacy": "party_shared",
            },
            headers=bearer(PLAYER_SUBJECT),
        )
        assert published.status_code == 201, published.text
        entry_id = published.json()["entry_id"]

    app = _boot_lore_process(redis_double)
    with TestClient(app) as second:
        listed = second.get(
            f"/api/v1/campaigns/{campaign_id}/codex/entries",
            headers=bearer(PLAYER_SUBJECT),
        )

    assert listed.status_code == 200, listed.text
    assert [entry["entry_id"] for entry in listed.json()] == [entry_id]


@pytest.mark.asyncio
async def test_lore_document_is_searchable_after_process_restart(
    isolated_campaign_lore_modules: None, redis_double: MockAsyncRedis
) -> None:
    """A document ingested before a restart is returned by search after the restart."""
    from fastapi.testclient import TestClient

    campaign_id = str(uuid4())
    await _seed_campaign(campaign_id)

    app = _boot_lore_process(redis_double)
    with TestClient(app) as first:
        ingested = first.post(
            "/api/v1/lore/documents",
            json={
                "campaign_id": campaign_id,
                "title": "Knights of the Sunblade",
                "content": "Sir Gareth wields the Sunblade against the undead.",
            },
            headers=bearer(DM_SUBJECT),
        )
        assert ingested.status_code == 200, ingested.text

    app = _boot_lore_process(redis_double)
    with TestClient(app) as second:
        searched = second.post(
            "/api/v1/lore/search",
            json={"campaign_id": campaign_id, "query": "Sunblade undead", "limit": 5},
            headers=bearer(PLAYER_SUBJECT),
        )

    assert searched.status_code == 200, searched.text
    titles = [result["document_title"] for result in searched.json()["results"]]
    assert titles == ["Knights of the Sunblade"]
