"""Blackbox frontdoor tests for the Campaign Lore pgvector store and embedding port (TASK-0670).

Governed by ADR-0015 (fail fast, no fallback to fakes) and Hard Invariant 7.

Setup goes through public HTTP routes and environment settings. The only stand-in is the
OpenAI-compatible embeddings endpoint, an external process boundary. Start-up behaviour is
observed through the lifespan of the public application.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.identity import set_zitadel_auth_service
from campaign_lore.main import create_app
from fastapi.testclient import TestClient
from pydantic import ValidationError
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.config import LoreBackendSettings

from tests.helpers.live_services import closed_port_url, serve
from tests.helpers.lore_backends import (
    LORE_DOCUMENTS,
    LORE_EMBEDDING_DIMENSION,
    LORE_EMBEDDING_MODEL,
    TREASURE_QUERY,
    UNDEAD_QUERY,
    UNDEAD_TITLE,
    VAULT_TITLE,
    lore_embedding_app,
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


@pytest.fixture(autouse=True)
def _trust_signing_issuer():
    """Campaign Lore verifies bearer tokens with the test issuer for each test in this module."""
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    yield
    set_zitadel_auth_service(None)


@pytest.fixture
def client(lore_backends: dict[str, str | int]) -> Iterator[TestClient]:
    with TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)) as client:
        yield client


def _closed_port() -> int:
    """Return a loopback port where nothing listens."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _ingest_two_documents(client: TestClient, campaign_id: str) -> None:
    for title, content in LORE_DOCUMENTS:
        resp = client.post(
            "/api/v1/lore/documents",
            json={"campaign_id": campaign_id, "title": title, "content": content},
        )
        assert resp.status_code == 200, resp.text


def _ranked_titles(client: TestClient, campaign_id: str, query: str) -> list[str]:
    resp = client.post(
        "/api/v1/lore/search",
        json={"campaign_id": campaign_id, "query": query, "limit": 5},
    )
    assert resp.status_code == 200, resp.text
    return [result["document_title"] for result in resp.json()["results"]]


@pytest.mark.asyncio
async def test_query_close_in_meaning_ranks_the_matching_document_first(client: TestClient) -> None:
    """A phrase that shares no word with a document still ranks that document first."""
    campaign_id = str(uuid4())
    await _seed_dm(campaign_id)
    _ingest_two_documents(client, campaign_id)

    undead_titles = _ranked_titles(client, campaign_id, UNDEAD_QUERY)
    treasure_titles = _ranked_titles(client, campaign_id, TREASURE_QUERY)

    assert undead_titles[:1] == [UNDEAD_TITLE]
    assert treasure_titles[:1] == [VAULT_TITLE]


def test_settings_reject_in_memory_and_fake_backends() -> None:
    """Production settings have no choice for the in-process vector index or the fake embedder."""
    with pytest.raises(ValidationError):
        LoreBackendSettings(vector="memory")
    with pytest.raises(ValidationError):
        LoreBackendSettings(embedding="fake")


def test_start_up_fails_when_embedding_endpoint_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The service refuses to start when the configured embeddings endpoint does not answer."""
    monkeypatch.setenv("RUNEFOBLE_EMBEDDING_BASE_URL", f"{closed_port_url()}/v1")
    monkeypatch.setenv("RUNEFOBLE_EMBEDDING_MODEL", LORE_EMBEDDING_MODEL)
    monkeypatch.setenv("RUNEFOBLE_EMBEDDING_DIMENSION", str(LORE_EMBEDDING_DIMENSION))

    with (
        pytest.raises(RuntimeError, match="embedding endpoint is unreachable"),
        TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)),
    ):
        pass


def test_start_up_fails_when_pgvector_store_is_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The service refuses to start with a clear error when PostgreSQL does not answer."""
    dead_port = _closed_port()
    with serve(lore_embedding_app()) as embedding_url:
        monkeypatch.setenv("RUNEFOBLE_EMBEDDING_BASE_URL", f"{embedding_url}/v1")
        monkeypatch.setenv("RUNEFOBLE_EMBEDDING_MODEL", LORE_EMBEDDING_MODEL)
        monkeypatch.setenv("RUNEFOBLE_EMBEDDING_DIMENSION", str(LORE_EMBEDDING_DIMENSION))
        monkeypatch.setenv(
            "RUNEFOBLE_DATABASE_URL",
            f"postgresql+asyncpg://u:p@127.0.0.1:{dead_port}/lore",
        )

        with (
            pytest.raises(RuntimeError, match="vector store .* is unreachable"),
            TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)),
        ):
            pass


def test_embedding_endpoint_settings_are_required_by_the_default_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With no endpoint configured, start-up names every missing setting."""
    for name in (
        "RUNEFOBLE_EMBEDDING_BASE_URL",
        "RUNEFOBLE_EMBEDDING_MODEL",
        "RUNEFOBLE_EMBEDDING_DIMENSION",
    ):
        monkeypatch.delenv(name, raising=False)

    with (
        pytest.raises(ValueError, match="RUNEFOBLE_EMBEDDING_BASE_URL"),
        TestClient(create_app(), headers=_bearer(VISITOR_SUBJECT)),
    ):
        pass
