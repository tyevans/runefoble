"""Blackbox TDD tests for Campaign Lore Knowledge Base & redstring RAG Microservice.

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
All assertions and setup operate strictly through public HTTP endpoints
using TestClient(app) from campaign_lore.main.
"""

import time
from uuid import uuid4

import pytest
from campaign_lore.dependencies import get_spicedb_client
from campaign_lore.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_blackbox_document_ingestion_and_retrieval(client: TestClient):
    """Test public frontdoor ingestion of worldbuilding lore documents with event sourcing."""
    campaign_id = str(uuid4())

    # 1. Frontdoor document ingestion
    payload = {
        "campaign_id": campaign_id,
        "title": "The Knights of the Silver Dawn",
        "content": "Sir Gareth is also known as The Silver Knight. He guards the Citadel of Light in Neverwinter.",
        "is_secret": False,
        "tags": ["factions", "paladins"],
    }
    resp = client.post("/api/v1/lore/documents", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "document_id" in data
    doc_id = data["document_id"]
    assert data["campaign_id"] == campaign_id
    assert data["title"] == "The Knights of the Silver Dawn"
    assert data["is_secret"] is False
    assert data["status"] == "indexed"
    assert data["entities_count"] >= 1
    assert data["chunks_count"] >= 1

    # 2. Public GET frontdoor document lookup
    get_resp = client.get(f"/api/v1/lore/documents/{doc_id}")
    assert get_resp.status_code == 200, get_resp.text
    doc_state = get_resp.json()
    assert doc_state["document_id"] == doc_id
    assert doc_state["campaign_id"] == campaign_id
    assert doc_state["title"] == "The Knights of the Silver Dawn"
    assert len(doc_state["entities"]) >= 1


@pytest.mark.asyncio
async def test_blackbox_alias_consolidation(client: TestClient):
    """Test alias consolidation via redstring merging 'The Silver Knight' to canonical 'Sir Gareth'."""
    campaign_id = str(uuid4())

    # 1. Ingest lore document introducing the character and title
    ingest_payload = {
        "campaign_id": campaign_id,
        "title": "Heroes of the Sword Coast",
        "content": "Sir Gareth is also known as The Silver Knight. He serves with honor.",
        "is_secret": False,
    }
    ingest_resp = client.post("/api/v1/lore/documents", json=ingest_payload)
    assert ingest_resp.status_code == 200
    doc_id = ingest_resp.json()["document_id"]

    # 2. Consolidate alias via public endpoint
    alias_payload = {
        "campaign_id": campaign_id,
        "canonical_name": "Sir Gareth",
        "alias_name": "The Silver Knight",
        "reason": "Title of valor",
        "document_id": doc_id,
    }
    consol_resp = client.post("/api/v1/lore/aliases/consolidate", json=alias_payload)
    assert consol_resp.status_code == 200, consol_resp.text
    consol_data = consol_resp.json()
    assert consol_data["canonical_name"] == "Sir Gareth"
    assert consol_data["alias_name"] == "The Silver Knight"
    assert consol_data["status"] == "consolidated"

    # 3. Resolve alias via public lookup
    res_resp = client.get(
        f"/api/v1/lore/aliases/resolve?campaign_id={campaign_id}&name=The+Silver+Knight"
    )
    assert res_resp.status_code == 200, res_resp.text
    res_data = res_resp.json()
    assert res_data["input_name"] == "The Silver Knight"
    assert res_data["canonical_name"] == "Sir Gareth"
    assert res_data["is_alias"] is True

    # 4. Resolve canonical name returns itself
    canon_resp = client.get(
        f"/api/v1/lore/aliases/resolve?campaign_id={campaign_id}&name=Sir+Gareth"
    )
    assert canon_resp.status_code == 200
    assert canon_resp.json()["canonical_name"] == "Sir Gareth"


@pytest.mark.asyncio
async def test_blackbox_sub_50ms_hybrid_search(client: TestClient):
    """Test sub-50ms hybrid RAG search combining BM25, dense embeddings, and graph traversal."""
    campaign_id = str(uuid4())

    # Ingest multiple lore documents to populate graph and chunks
    docs = [
        {
            "campaign_id": campaign_id,
            "title": "The Citadel of Light",
            "content": "The Citadel of Light is located in Neverwinter. It is protected by sacred sun wards.",
            "is_secret": False,
        },
        {
            "campaign_id": campaign_id,
            "title": "Sir Gareth and the Sunblade",
            "content": "Sir Gareth wields the legendary Sunblade to banish fiends and undead abominations.",
            "is_secret": False,
        },
    ]

    for d in docs:
        resp = client.post("/api/v1/lore/documents", json=d)
        assert resp.status_code == 200

    # Execute search query
    search_payload = {
        "campaign_id": campaign_id,
        "query": "Sunblade undead banish",
        "limit": 5,
        "include_graph_walk": True,
    }

    t0 = time.perf_counter()
    search_resp = client.post("/api/v1/lore/search", json=search_payload)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert search_resp.status_code == 200, search_resp.text
    search_data = search_resp.json()

    # Sub-50ms hybrid retrieval validation
    assert elapsed_ms < 50.0, f"Search took {elapsed_ms}ms, exceeding 50ms SLA"
    assert search_data["took_ms"] < 50.0

    # Validate hybrid retrieval matches
    assert search_data["results_count"] >= 1
    top_result = search_data["results"][0]
    assert "Sunblade" in top_result["text"]
    assert top_result["score"] > 0
    assert top_result["document_title"] == "Sir Gareth and the Sunblade"
    assert top_result["is_secret"] is False


@pytest.mark.asyncio
async def test_blackbox_spicedb_authorization_secret_filtering(client: TestClient):
    """Verify SpiceDB Zanzibar authorization filters secret DM lore for players."""
    campaign_id = str(uuid4())
    dm_user = f"dm-{uuid4().hex[:6]}"
    player_user = f"player-{uuid4().hex[:6]}"
    spicedb = get_spicedb_client()

    # Establish SpiceDB Zanzibar relationships
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="dungeon_master",
        subject_type="user",
        subject_id=dm_user,
    )
    await spicedb.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="player",
        subject_type="user",
        subject_id=player_user,
    )

    # 1. Ingest public document
    client.post(
        "/api/v1/lore/documents",
        json={
            "campaign_id": campaign_id,
            "title": "Phandalin Town Hall",
            "content": "The town hall of Phandalin is maintained by Harbin Wester.",
            "is_secret": False,
        },
    )

    # 2. Ingest secret DM-only lore document
    secret_resp = client.post(
        "/api/v1/lore/documents",
        json={
            "campaign_id": campaign_id,
            "title": "Redbrand Hideout Secret Vault",
            "content": "Underneath Tresendar Manor lies the secret vault containing the cursed Dragon Eye gem.",
            "is_secret": True,
        },
    )
    assert secret_resp.status_code == 200
    secret_doc_id = secret_resp.json()["document_id"]

    # 3. Direct document access check
    # DM can view secret document
    dm_doc_resp = client.get(
        f"/api/v1/lore/documents/{secret_doc_id}",
        headers={"x-user-id": dm_user},
    )
    assert dm_doc_resp.status_code == 200
    assert dm_doc_resp.json()["is_secret"] is True

    # Player CANNOT view secret document directly (403 Forbidden)
    player_doc_resp = client.get(
        f"/api/v1/lore/documents/{secret_doc_id}",
        headers={"x-user-id": player_user},
    )
    assert player_doc_resp.status_code == 403
    assert "Forbidden" in player_doc_resp.json()["detail"]

    # 4. Search filtering check
    search_query = {
        "campaign_id": campaign_id,
        "query": "Dragon Eye gem secret vault",
        "limit": 10,
    }

    # DM search should retrieve the secret document
    dm_search = client.post(
        "/api/v1/lore/search",
        json=search_query,
        headers={"x-user-id": dm_user},
    )
    assert dm_search.status_code == 200
    dm_results = dm_search.json()
    assert dm_results["can_read_secrets"] is True
    assert any("Dragon Eye gem" in r["text"] for r in dm_results["results"]), (
        "DM should receive secret lore results"
    )

    # Player search MUST NOT retrieve secret document
    player_search = client.post(
        "/api/v1/lore/search",
        json=search_query,
        headers={"x-user-id": player_user},
    )
    assert player_search.status_code == 200
    player_results = player_search.json()
    assert player_results["can_read_secrets"] is False
    assert not any("Dragon Eye gem" in r["text"] for r in player_results["results"]), (
        "Player must NEVER see secret DM lore"
    )


def test_blackbox_openapi_and_ui_manifest(client: TestClient):
    """Verify OpenAPI and UI manifest compliance with Hard Invariants 3 and 5."""
    # Hard Invariant 5: OpenAPI spec exposed at /openapi.json
    open_resp = client.get("/openapi.json")
    assert open_resp.status_code == 200
    spec = open_resp.json()
    assert "/api/v1/lore/documents" in spec["paths"]
    assert "/api/v1/lore/search" in spec["paths"]
    assert "/api/v1/lore/aliases/consolidate" in spec["paths"]

    # Hard Invariant 3 / DoD 2: UI manifest advertising vendored microfrontend
    manifest_resp = client.get("/ui/manifest")
    assert manifest_resp.status_code == 200
    manifest = manifest_resp.json()
    assert manifest["service"] == "campaign_lore"
    assert manifest["package"] == "@runefoble/campaign-lore-ui"
    assert "runefoble-campaign-codex" in manifest["components"]
