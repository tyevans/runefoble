"""Blackbox frontdoor tests: Campaign Lore takes the caller only from the verified bearer token.

Governed by TASK-0531, ADR-0015 (c), US-0013, and Hard Invariant 7. Every request goes through
public HTTP routes. Tokens are RS256 tokens minted by the test issuer that the service trusts.
Body `caller_id` and `x-user-id` headers must have no effect on identity.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.identity import set_zitadel_auth_service
from campaign_lore.main import app
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from runefoble_auth.spicedb import SpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer

from tests.helpers.ws_identity import SIGNING_ISSUER

PUBLIC_PATHS = {
    "/health",
    "/healthz",
    "/openapi.json",
    "/ui/manifest",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}
SECRET_TITLE = "Vault of the Dragon Eye"


def _bearer(user_id: str, issuer: SigningTestIssuer = SIGNING_ISSUER) -> dict[str, str]:
    """Return headers carrying a signed bearer token for `user_id`."""
    return {"Authorization": f"Bearer {issuer.mint(user_id)}"}


@pytest.fixture(autouse=True)
def _trust_signing_issuer() -> Iterator[None]:
    set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    yield
    set_zitadel_auth_service(None)


@pytest.fixture
def client(lore_backends) -> Iterator[TestClient]:
    with TestClient(app) as lore_client:
        yield lore_client


@pytest.fixture
def seeded_campaign() -> dict[str, str]:
    """Return a campaign id, a DM id, and a player id. Relations are seeded by `_seed_members`."""
    return {"id": str(uuid4()), "dm": f"dm-{uuid4().hex[:6]}", "player": f"pl-{uuid4().hex[:6]}"}


async def _seed_members(spicedb_client: SpiceDBClient, campaign: dict[str, str]) -> None:
    """Grant the DM and player their campaign roles. Campaign Lore has no membership frontdoor."""
    await spicedb_client.write_relationship(
        "campaign", campaign["id"], "dungeon_master", "user", campaign["dm"]
    )
    await spicedb_client.write_relationship(
        "campaign", campaign["id"], "player", "user", campaign["player"]
    )


def _ingest_secret(client: TestClient, campaign: dict[str, str]) -> None:
    res = client.post(
        "/api/v1/lore/documents",
        json={
            "campaign_id": campaign["id"],
            "title": SECRET_TITLE,
            "content": "The Dragon Eye gem rests in a secret vault beneath the Citadel.",
            "is_secret": True,
        },
        headers=_bearer(campaign["dm"]),
    )
    assert res.status_code == 200, res.text


def _search(client: TestClient, body: dict, headers: dict[str, str]):
    return client.post("/api/v1/lore/search", json=body, headers=headers)


@pytest.mark.asyncio
async def test_player_body_caller_id_naming_dm_reads_no_secret(
    client: TestClient, seeded_campaign: dict[str, str]
) -> None:
    """The audit probe: a player names the DM in the body and gets no secret chunk."""
    await _seed_members(get_spicedb_client(), seeded_campaign)
    _ingest_secret(client, seeded_campaign)
    body = {
        "campaign_id": seeded_campaign["id"],
        "query": "Dragon Eye gem secret vault",
        "caller_id": seeded_campaign["dm"],
        "limit": 10,
    }

    res = _search(client, body, _bearer(seeded_campaign["player"]))

    assert res.status_code == 422, res.text
    assert "caller_id" in res.text


@pytest.mark.asyncio
async def test_player_spoofed_user_header_reads_no_secret(
    client: TestClient, seeded_campaign: dict[str, str]
) -> None:
    """A player token with an `x-user-id` header naming the DM gets the player's view only."""
    await _seed_members(get_spicedb_client(), seeded_campaign)
    _ingest_secret(client, seeded_campaign)
    body = {"campaign_id": seeded_campaign["id"], "query": "Dragon Eye gem secret vault"}
    headers = {**_bearer(seeded_campaign["player"]), "x-user-id": seeded_campaign["dm"]}

    res = _search(client, body, headers)

    assert res.status_code == 200, res.text
    assert res.json()["can_read_secrets"] is False
    assert SECRET_TITLE not in [r["document_title"] for r in res.json()["results"]]


@pytest.mark.asyncio
async def test_dm_token_reads_secret_chunk(
    client: TestClient, seeded_campaign: dict[str, str]
) -> None:
    """The verified subject is the DM, so the DM search returns the secret chunk."""
    await _seed_members(get_spicedb_client(), seeded_campaign)
    _ingest_secret(client, seeded_campaign)
    body = {"campaign_id": seeded_campaign["id"], "query": "Dragon Eye gem secret vault"}

    res = _search(client, body, _bearer(seeded_campaign["dm"]))

    assert res.status_code == 200, res.text
    assert res.json()["can_read_secrets"] is True
    assert SECRET_TITLE in [r["document_title"] for r in res.json()["results"]]


@pytest.mark.asyncio
async def test_search_without_bearer_is_refused(
    client: TestClient, seeded_campaign: dict[str, str]
) -> None:
    await _seed_members(get_spicedb_client(), seeded_campaign)
    res = client.post(
        "/api/v1/lore/search",
        json={"campaign_id": seeded_campaign["id"], "query": "Dragon Eye"},
        headers={"x-user-id": seeded_campaign["dm"]},
    )

    assert res.status_code == 401
    assert res.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_token_from_untrusted_issuer_is_refused(
    client: TestClient, seeded_campaign: dict[str, str]
) -> None:
    await _seed_members(get_spicedb_client(), seeded_campaign)
    rogue = SigningTestIssuer(issuer="http://rogue.test")

    res = _search(
        client,
        {"campaign_id": seeded_campaign["id"], "query": "Dragon Eye"},
        _bearer(seeded_campaign["dm"], rogue),
    )

    assert res.status_code == 401


def test_every_campaign_lore_route_requires_a_bearer(client: TestClient) -> None:
    """No campaign-lore route answers an anonymous caller. Only the public surface stays open."""
    spec = client.get("/openapi.json").json()
    protected = [
        (method.upper(), template)
        for template, operations in spec["paths"].items()
        if template not in PUBLIC_PATHS
        for method in operations
    ]
    assert protected, "campaign_lore exposes no protected routes"

    for method, template in protected:
        path = re.sub(r"\{[^}]+\}", lambda _match: str(uuid4()), template)
        res = client.request(method, path, json={})
        assert res.status_code == 401, f"{method} {template} answered {res.status_code}"


def test_public_routes_stay_open(client: TestClient) -> None:
    assert client.get("/health").status_code == 200
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/ui/manifest").status_code == 200


@pytest.mark.parametrize(
    ("route", "body", "actor_field"),
    [
        (
            "/api/v1/lore/documents",
            {"title": "t", "content": "c", "author_id": "other-user"},
            "author_id",
        ),
        (
            "/api/v1/lore/handouts/{id}/break-seal",
            {"break_force": 14.0, "broken_by": "other-user"},
            "broken_by",
        ),
        (
            "/api/v1/lore/handouts/{id}/reveal-invisible-ink",
            {"uv_intensity": 1.0, "revealed_by": "other-user"},
            "revealed_by",
        ),
        (
            "/api/v1/lore/relics/{id}/inspect",
            {"notes": "n", "inspected_by": "other-user"},
            "inspected_by",
        ),
    ],
)
def test_body_actor_field_is_refused_and_actor_is_the_verified_subject(
    client: TestClient, route: str, body: dict[str, str], actor_field: str
) -> None:
    """A body naming another actor fails validation. The actor is never read from the body."""
    path = route.replace("{id}", str(uuid4()))

    res = client.post(path, json=body, headers=_bearer("verified-player"))

    assert res.status_code == 422, res.text
    assert actor_field in res.text
