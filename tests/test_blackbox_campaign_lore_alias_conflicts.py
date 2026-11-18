"""Blackbox frontdoor tests for Campaign Lore alias conflicts and retrieval wiring (TASK-0673).

Governed by:
- ADR-0015 (b) and (c): a conflict is a client error (409); a missing backend is 503, never 500.
- Hard Invariant 7: all setup and assertions go through public HTTP routes.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.identity import set_zitadel_auth_service
from campaign_lore.main import app, create_app
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client

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


@pytest.fixture(autouse=True)
def _trust_signing_issuer():
    """Campaign Lore verifies bearer tokens with the test issuer for each test in this module."""
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    yield
    set_zitadel_auth_service(None)


@pytest.fixture
def client(lore_backends) -> Iterator[TestClient]:
    with TestClient(app, headers=_bearer(VISITOR_SUBJECT)) as client:
        yield client


def _ingest(client: TestClient, campaign_id: str, title: str, content: str) -> str:
    resp = client.post(
        "/api/v1/lore/documents",
        json={"campaign_id": campaign_id, "title": title, "content": content},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["document_id"]


@pytest.mark.asyncio
async def test_repeated_alias_merge_returns_409_and_records_one_alias(client: TestClient):
    """A second identical merge is a conflict. The document keeps one consolidation."""
    campaign_id = str(uuid4())
    await _seed_dm(campaign_id)
    doc_id = _ingest(
        client,
        campaign_id,
        "Ledger of Vance",
        "Mirela Vance keeps the ledger. Mirela is the name the tavern uses.",
    )
    payload = {
        "campaign_id": campaign_id,
        "canonical_name": "Mirela Vance",
        "alias_name": "Mirela",
        "reason": "Same person",
        "document_id": doc_id,
    }

    first = client.post("/api/v1/lore/aliases/consolidate", json=payload)
    assert first.status_code == 200, first.text

    second = client.post("/api/v1/lore/aliases/consolidate", json=payload)
    assert second.status_code == 409, second.text
    assert "already" in second.json()["detail"]

    doc = client.get(f"/api/v1/lore/documents/{doc_id}")
    assert doc.status_code == 200, doc.text
    assert len(doc.json()["consolidated_aliases"]) == 1


@pytest.mark.asyncio
async def test_alias_that_is_already_a_canonical_target_conflicts_with_409(client: TestClient):
    """Merging into an entity that is itself an alias is a conflict, not a server fault."""
    campaign_id = str(uuid4())
    await _seed_dm(campaign_id)
    doc_id = _ingest(
        client,
        campaign_id,
        "Court Records",
        "Sir Corin holds the keep. The Red Hand is his other name.",
    )
    first = client.post(
        "/api/v1/lore/aliases/consolidate",
        json={
            "campaign_id": campaign_id,
            "canonical_name": "Sir Corin",
            "alias_name": "The Red Hand",
            "document_id": doc_id,
        },
    )
    assert first.status_code == 200, first.text

    conflict = client.post(
        "/api/v1/lore/aliases/consolidate",
        json={
            "campaign_id": campaign_id,
            "canonical_name": "The Red Hand",
            "alias_name": "Sir Corin",
            "document_id": doc_id,
        },
    )
    assert conflict.status_code == 409, conflict.text


def test_consolidate_without_started_service_returns_503_with_message():
    """An application that never ran its lifespan reports a missing backend as 503."""
    client = TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT))
    resp = client.post(
        "/api/v1/lore/aliases/consolidate",
        json={
            "campaign_id": str(uuid4()),
            "canonical_name": "Sir Gareth",
            "alias_name": "The Silver Knight",
            "document_id": str(uuid4()),
        },
    )
    assert resp.status_code == 503, resp.text
    assert resp.json()["detail"] == "campaign_lore is not started"


def test_openapi_documents_409_and_503_for_consolidate_route():
    """OpenAPI lists the conflict and unavailable responses for the consolidate route."""
    spec = TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)).get("/openapi.json").json()
    responses = spec["paths"]["/api/v1/lore/aliases/consolidate"]["post"]["responses"]
    assert "409" in responses
    assert "503" in responses
