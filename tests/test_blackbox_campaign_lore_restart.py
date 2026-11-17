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

import pytest
from campaign_lore.dependencies import get_spicedb_client
from campaign_lore.main import create_app
from fastapi.testclient import TestClient
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import get_event_store, set_event_store


def _use_postgres_event_store(dsn: str):
    """Build a fresh PostgreSQL event store and make it the process-wide store."""
    settings = PlatformSettings(database_url=dsn, use_postgres_event_store=True)
    store = get_event_store(settings=settings, force_new=True)
    set_event_store(store)
    return store


@pytest.fixture(autouse=True)
def reset_event_store_singleton():
    set_event_store(None)
    yield
    set_event_store(None)


@pytest.mark.asyncio
async def test_lore_projection_survives_restart(postgres_service):
    """Documents, aliases, and secrecy rules hold after a restart on the same event store."""
    if not postgres_service:
        pytest.skip("Docker not available for PostgreSQL event store test")

    dsn = str(postgres_service["dsn"])
    campaign_id = str(uuid4())
    dm_user = f"dm-{uuid4().hex[:6]}"
    player_user = f"player-{uuid4().hex[:6]}"
    spicedb = get_spicedb_client()
    await spicedb.write_relationship("campaign", campaign_id, "run_session", "user", dm_user)

    store_before = _use_postgres_event_store(dsn)
    with TestClient(create_app()) as first:
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
    with TestClient(create_app()) as second:
        player_search = second.post(
            "/api/v1/lore/search",
            json={
                "campaign_id": campaign_id,
                "query": "Sunblade undead",
                "caller_id": player_user,
                "limit": 5,
            },
        )
        assert player_search.status_code == 200, player_search.text
        titles = [r["document_title"] for r in player_search.json()["results"]]
        assert "Knights of the Sunblade" in titles

        secret_for_player = second.post(
            "/api/v1/lore/search",
            json={
                "campaign_id": campaign_id,
                "query": "Dragon Eye gem secret vault",
                "caller_id": player_user,
                "limit": 5,
            },
        )
        assert "Vault of the Dragon Eye" not in [
            r["document_title"] for r in secret_for_player.json()["results"]
        ]

        secret_for_dm = second.post(
            "/api/v1/lore/search",
            json={
                "campaign_id": campaign_id,
                "query": "Dragon Eye gem secret vault",
                "caller_id": dm_user,
                "limit": 5,
            },
        )
        assert "Vault of the Dragon Eye" in [
            r["document_title"] for r in secret_for_dm.json()["results"]
        ]

        resolve = second.get(
            "/api/v1/lore/aliases/resolve",
            params={"campaign_id": campaign_id, "name": "The Silver Knight"},
        )
        assert resolve.json()["canonical_name"] == "Sir Gareth"

        doc = second.get(f"/api/v1/lore/documents/{public_id}", headers={"x-user-id": player_user})
        assert doc.status_code == 200, doc.text
        assert doc.json()["title"] == "Knights of the Sunblade"
    await store_after.close()


def test_extracted_entities_record_pattern_provenance():
    """Entities from regex extraction are recorded as pattern extraction, never as LLM output."""
    set_event_store(None)
    campaign_id = str(uuid4())
    with TestClient(create_app()) as client:
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


def test_alias_consolidation_requires_an_existing_document():
    """A consolidation cannot be recorded against a document that does not exist."""
    set_event_store(None)
    with TestClient(create_app()) as client:
        resp = client.post(
            "/api/v1/lore/aliases/consolidate",
            json={
                "campaign_id": str(uuid4()),
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
        "RUNEFOBLE_USE_POSTGRES_EVENT_STORE": "true",
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
