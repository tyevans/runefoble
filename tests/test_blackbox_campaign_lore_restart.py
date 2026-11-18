"""Blackbox frontdoor tests for Campaign Lore durability and start-up.

Governed by:
- ADR-0011: Core Event Sourcing with eventsource-py (the event store is the source of truth)
- ADR-0014: BDD and frontdoor test setup
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

All setup goes through public HTTP routes. A restart is a new application instance with
a new PostgreSQL event store connection, which is what a real process restart does.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from uuid import uuid4

import asyncpg
import pytest
from campaign_lore.main import create_app
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import get_event_store, set_event_store

from tests.helpers.lore_backends import (
    LORE_DOCUMENTS,
    TREASURE_QUERY,
    UNDEAD_QUERY,
)
from tests.helpers.ws_identity import SIGNING_ISSUER

VISITOR_SUBJECT = "lore-test-visitor"


async def _seed_dm(campaign_id: str, user_id: str = VISITOR_SUBJECT) -> None:
    """Make `user_id` the DM of a fresh campaign. Campaign Lore has no membership frontdoor."""
    await get_spicedb_client().write_relationship(
        "campaign", campaign_id, "dungeon_master", "user", user_id
    )


def _bearer(user_id: str) -> dict[str, str]:
    """Return headers carrying a signed bearer token for `user_id`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(user_id)}"}


def _use_postgres_event_store(dsn: str):
    """Build a fresh PostgreSQL event store and make it the process-wide store."""
    settings = PlatformSettings(database_url=dsn, event_store_backend="postgresql")
    store = get_event_store(settings=settings, force_new=True)
    set_event_store(store)
    return store


async def _vector_rows(dsn: str, campaign_id: str) -> int:
    """Count the pgvector entity rows that one campaign tenant owns. An observation only."""
    connection = await asyncpg.connect(dsn)
    try:
        return int(
            await connection.fetchval(
                "SELECT count(*) FROM lore_entity_vectors WHERE tenant_id = $1::uuid",
                campaign_id,
            )
        )
    finally:
        await connection.close()


def _ranked_titles(client: TestClient, campaign_id: str, query: str) -> list[str]:
    resp = client.post(
        "/api/v1/lore/search", json={"campaign_id": campaign_id, "query": query, "limit": 5}
    )
    assert resp.status_code == 200, resp.text
    return [result["document_title"] for result in resp.json()["results"]]


@pytest.fixture(autouse=True)
def reset_event_store_singleton():
    set_event_store(None)
    yield
    set_event_store(None)


@pytest.mark.asyncio
@pytest.mark.usefixtures("lore_backends")
async def test_pgvector_ranking_survives_restart_without_reingest(postgres_service):
    """A restart on the same PostgreSQL fixture keeps the ranking and one row per entity."""
    if not postgres_service:
        pytest.skip("Docker not available for PostgreSQL pgvector test")

    dsn = str(postgres_service["dsn"])
    campaign_id = str(uuid4())
    await _seed_dm(campaign_id)

    store_before = _use_postgres_event_store(dsn)
    with TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)) as first:
        for title, content in LORE_DOCUMENTS:
            resp = first.post(
                "/api/v1/lore/documents",
                json={"campaign_id": campaign_id, "title": title, "content": content},
            )
            assert resp.status_code == 200, resp.text
        undead_before = _ranked_titles(first, campaign_id, UNDEAD_QUERY)
        treasure_before = _ranked_titles(first, campaign_id, TREASURE_QUERY)
    await store_before.close()
    rows_before = await _vector_rows(dsn, campaign_id)

    store_after = _use_postgres_event_store(dsn)
    with TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)) as second:
        undead_after = _ranked_titles(second, campaign_id, UNDEAD_QUERY)
        treasure_after = _ranked_titles(second, campaign_id, TREASURE_QUERY)
    await store_after.close()
    rows_after = await _vector_rows(dsn, campaign_id)

    assert undead_after[:1] == [LORE_DOCUMENTS[0][0]]
    assert undead_before == undead_after
    assert treasure_before == treasure_after
    assert rows_before > 0
    assert rows_after == rows_before


@pytest.mark.asyncio
@pytest.mark.usefixtures("lore_backends")
async def test_lore_projection_survives_restart(postgres_service):
    """Documents, aliases, and secrecy rules hold after a restart on the same event store."""
    if not postgres_service:
        pytest.skip("Docker not available for PostgreSQL event store test")

    dsn = str(postgres_service["dsn"])
    campaign_id = str(uuid4())
    dm_user = f"dm-{uuid4().hex[:6]}"
    player_user = f"player-{uuid4().hex[:6]}"
    spicedb = get_spicedb_client()
    await spicedb.write_relationship("campaign", campaign_id, "dungeon_master", "user", dm_user)
    await _seed_dm(campaign_id)
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", player_user)

    store_before = _use_postgres_event_store(dsn)
    with TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)) as first:
        public_resp = first.post(
            "/api/v1/lore/documents",
            json={
                "campaign_id": campaign_id,
                "title": "Knights of the Sunblade",
                "content": (
                    "Sir Gareth wields the Sunblade against undead. "
                    "Sir Gareth guards the Citadel of Light."
                ),
            },
        )
        assert public_resp.status_code == 200, public_resp.text
        public_id = public_resp.json()["document_id"]

        secret_resp = first.post(
            "/api/v1/lore/documents",
            json={
                "campaign_id": campaign_id,
                "title": "Vault of the Dragon Eye",
                "content": "The Dragon Eye gem rests in a secret vault beneath the Citadel.",
                "is_secret": True,
            },
        )
        assert secret_resp.status_code == 200, secret_resp.text

        alias_resp = first.post(
            "/api/v1/lore/aliases/consolidate",
            json={
                "campaign_id": campaign_id,
                "canonical_name": "Sir Gareth",
                "alias_name": "The Silver Knight",
                "document_id": public_id,
            },
        )
        assert alias_resp.status_code == 200, alias_resp.text
    await store_before.close()

    store_after = _use_postgres_event_store(dsn)
    with TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)) as second:
        player_search = second.post(
            "/api/v1/lore/search",
            json={
                "campaign_id": campaign_id,
                "query": "Sunblade undead",
                "limit": 5,
            },
            headers=_bearer(player_user),
        )
        assert player_search.status_code == 200, player_search.text
        titles = [r["document_title"] for r in player_search.json()["results"]]
        assert "Knights of the Sunblade" in titles

        secret_for_player = second.post(
            "/api/v1/lore/search",
            json={
                "campaign_id": campaign_id,
                "query": "Dragon Eye gem secret vault",
                "limit": 5,
            },
            headers=_bearer(player_user),
        )
        assert "Vault of the Dragon Eye" not in [
            r["document_title"] for r in secret_for_player.json()["results"]
        ]

        secret_for_dm = second.post(
            "/api/v1/lore/search",
            json={
                "campaign_id": campaign_id,
                "query": "Dragon Eye gem secret vault",
                "limit": 5,
            },
            headers=_bearer(dm_user),
        )
        assert "Vault of the Dragon Eye" in [
            r["document_title"] for r in secret_for_dm.json()["results"]
        ]

        resolve = second.get(
            "/api/v1/lore/aliases/resolve",
            params={"campaign_id": campaign_id, "name": "The Silver Knight"},
        )
        assert resolve.json()["canonical_name"] == "Sir Gareth"

        doc = second.get(f"/api/v1/lore/documents/{public_id}", headers=_bearer(player_user))
        assert doc.status_code == 200, doc.text
        assert doc.json()["title"] == "Knights of the Sunblade"
    await store_after.close()


@pytest.mark.usefixtures("lore_backends")
@pytest.mark.asyncio
async def test_extracted_entities_record_pattern_provenance():
    """Entities from regex extraction are recorded as pattern extraction, never as LLM output."""
    set_event_store(None)
    campaign_id = str(uuid4())
    await _seed_dm(campaign_id)
    with TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)) as client:
        resp = client.post(
            "/api/v1/lore/documents",
            json={
                "campaign_id": campaign_id,
                "title": "Guardians of the Citadel",
                "content": "Sir Gareth guards Citadel of Light in Neverwinter.",
            },
        )
        assert resp.status_code == 200, resp.text
        doc_id = resp.json()["document_id"]

        doc = client.get(f"/api/v1/lore/documents/{doc_id}").json()

    methods = {e["extraction_method"] for e in doc["entities"]}
    assert methods == {"pattern"}
    assert any(e["name"] == "Sir Gareth" for e in doc["entities"])


@pytest.mark.asyncio
@pytest.mark.usefixtures("lore_backends")
async def test_alias_consolidation_requires_an_existing_document():
    """A consolidation cannot be recorded against a document that does not exist."""
    set_event_store(None)
    campaign_id = str(uuid4())
    await _seed_dm(campaign_id)
    with TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)) as client:
        resp = client.post(
            "/api/v1/lore/aliases/consolidate",
            json={
                "campaign_id": campaign_id,
                "canonical_name": "Sir Gareth",
                "alias_name": "The Silver Knight",
                "document_id": str(uuid4()),
            },
        )
    assert resp.status_code == 404


def test_start_up_fails_when_configured_event_store_is_unreachable():
    """The service exits with an error rather than serving an empty projection."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]

    env = {
        **os.environ,
        "RUNEFOBLE_EVENT_STORE_BACKEND": "postgresql",
        "RUNEFOBLE_DATABASE_URL": f"postgresql+asyncpg://u:p@127.0.0.1:{closed_port}/lore",
    }
    code = (
        "from fastapi.testclient import TestClient\n"
        "from campaign_lore.main import app\n"
        "with TestClient(app):\n"
        "    pass\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode != 0
    assert "unreachable" in result.stderr
