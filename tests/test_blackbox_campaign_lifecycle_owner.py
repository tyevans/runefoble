"""Blackbox tests: game_session owns campaign lifecycle, membership, and invites (TASK-0590).

Governed by ADR-0015 decision (a), ADR-0001 (SpiceDB writes after save), ADR-0011, and
Hard Invariant 7. Every test drives game_session over HTTP with signed bearer tokens.
Setup goes through public routes only (create, invite, join).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from game_session.campaign import clock
from game_session.campaign.repositories import (
    CampaignRepositories,
    build_campaign_repositories,
    set_campaign_repositories,
)
from game_session.main import app as session_app
from game_session.settlement.auth.tokens import set_zitadel_auth_service
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_auth.testing.signing_test_issuer import SigningTestIssuer
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_sourcing import build_event_store, get_event_store, set_event_store

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def issuer() -> Iterator[SigningTestIssuer]:
    signing = SigningTestIssuer()
    set_zitadel_auth_service(signing.verifier())
    yield signing
    set_zitadel_auth_service(None)


@pytest.fixture(autouse=True)
def reset_process_globals() -> Iterator[None]:
    """Clear the event store and campaign repository singletons around every test.

    The PostgreSQL restart test binds both to a container that its module fixture stops.
    Without this reset, later modules inherit a store that points at a closed port.
    """
    set_event_store(None)
    set_campaign_repositories(None)
    yield
    set_event_store(None)
    set_campaign_repositories(None)


@pytest.fixture
def repos() -> Iterator[CampaignRepositories]:
    built = build_campaign_repositories()
    set_campaign_repositories(built)
    yield built
    set_campaign_repositories(None)


@pytest.fixture
def client(spicedb: MockSpiceDBClient, repos: CampaignRepositories) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


def auth(issuer: SigningTestIssuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def create_campaign(client: TestClient, issuer: SigningTestIssuer, owner: str = "dm-evelyn") -> str:
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Shadows of Drakkenheim", "setting": "Gothic Fantasy"},
        headers=auth(issuer, owner),
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def create_invite(
    client: TestClient,
    issuer: SigningTestIssuer,
    campaign_id: str,
    body: dict[str, Any] | None = None,
    owner: str = "dm-evelyn",
) -> str:
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json=body or {"role": "player"},
        headers=auth(issuer, owner),
    )
    assert res.status_code == 201, res.text
    return res.json()["token"]


def join(client: TestClient, issuer: SigningTestIssuer, token: str, user: str) -> Any:
    return client.post(
        "/api/v1/campaigns/join", json={"invite_token": token}, headers=auth(issuer, user)
    )


def test_created_campaign_is_readable_by_owner_with_lobby_session(
    client: TestClient, issuer: SigningTestIssuer, spicedb: MockSpiceDBClient
) -> None:
    res = client.post(
        "/api/v1/campaigns",
        json={"title": "Shadows of Drakkenheim", "setting": "Gothic Fantasy"},
        headers=auth(issuer, "dm-evelyn"),
    )
    assert res.status_code == 201
    body = res.json()
    assert body["role"] == "owner"
    assert body["member_count"] == 1
    assert body["owner_id"] == "dm-evelyn"

    got = client.get(f"/api/v1/campaigns/{body['id']}", headers=auth(issuer, "dm-evelyn"))
    assert got.status_code == 200
    assert got.json()["title"] == "Shadows of Drakkenheim"

    sessions = client.get(
        f"/api/v1/campaigns/{body['id']}/sessions", headers=auth(issuer, "dm-evelyn")
    ).json()
    assert [s["title"] for s in sessions] == ["Session #1: Staging Lobby"]
    assert sessions[0]["status"] == "lobby"


def test_campaign_and_membership_survive_restart(
    client: TestClient,
    issuer: SigningTestIssuer,
    repos: CampaignRepositories,
    spicedb: MockSpiceDBClient,
) -> None:
    campaign_id = create_campaign(client, issuer)
    token = create_invite(client, issuer, campaign_id)
    assert join(client, issuer, token, "player-marcus").status_code == 200

    # A new process reads the same event store. No state may live only in memory.
    restarted = build_campaign_repositories()
    set_campaign_repositories(restarted)

    got = client.get(f"/api/v1/campaigns/{campaign_id}", headers=auth(issuer, "dm-evelyn"))
    assert got.status_code == 200
    members = client.get(
        f"/api/v1/campaigns/{campaign_id}/members", headers=auth(issuer, "dm-evelyn")
    ).json()
    assert {(m["user_id"], m["role"]) for m in members} == {
        ("dm-evelyn", "owner"),
        ("player-marcus", "player"),
    }


def test_invite_with_max_uses_one_accepts_one_join_and_rejects_the_second(
    client: TestClient, issuer: SigningTestIssuer
) -> None:
    campaign_id = create_campaign(client, issuer)
    token = create_invite(client, issuer, campaign_id, {"role": "player", "max_uses": 1})

    first = join(client, issuer, token, "player-marcus")
    assert first.status_code == 200
    assert first.json()["zanzibar_relation"] == (
        f"campaign:{campaign_id}#player@user:player-marcus"
    )

    second = join(client, issuer, token, "player-kyra")
    assert second.status_code == 409
    assert second.json()["detail"]["error"] == "invite_exhausted"


def test_expired_invite_returns_410(
    client: TestClient, issuer: SigningTestIssuer, monkeypatch: pytest.MonkeyPatch
) -> None:
    campaign_id = create_campaign(client, issuer)
    token = create_invite(client, issuer, campaign_id, {"role": "player", "expires_in_hours": 1})

    real_now = clock.utc_now()
    monkeypatch.setattr(clock, "utc_now", lambda: real_now + timedelta(hours=2))

    res = join(client, issuer, token, "player-marcus")
    assert res.status_code == 410
    assert res.json()["detail"]["error"] == "invite_expired"


def test_unknown_invite_token_returns_400(client: TestClient, issuer: SigningTestIssuer) -> None:
    res = join(client, issuer, "not-a-real-token", "player-marcus")
    assert res.status_code == 400
    assert res.json()["detail"]["error"] == "invalid_invite"


def test_removed_member_loses_roster_entry_and_view_access(
    client: TestClient, issuer: SigningTestIssuer, spicedb: MockSpiceDBClient
) -> None:
    campaign_id = create_campaign(client, issuer)
    token = create_invite(client, issuer, campaign_id)
    assert join(client, issuer, token, "player-marcus").status_code == 200

    removed = client.delete(
        f"/api/v1/campaigns/{campaign_id}/members/player-marcus",
        headers=auth(issuer, "dm-evelyn"),
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "member_removed"

    members = client.get(
        f"/api/v1/campaigns/{campaign_id}/members", headers=auth(issuer, "dm-evelyn")
    ).json()
    assert "player-marcus" not in {m["user_id"] for m in members}

    assert (
        client.get(
            f"/api/v1/campaigns/{campaign_id}", headers=auth(issuer, "player-marcus")
        ).status_code
        == 403
    )


def test_list_campaigns_omits_campaigns_the_caller_cannot_view(
    client: TestClient, issuer: SigningTestIssuer
) -> None:
    mine = create_campaign(client, issuer, owner="dm-evelyn")
    create_campaign(client, issuer, owner="dm-arthur")

    listed = client.get("/api/v1/campaigns", headers=auth(issuer, "dm-evelyn")).json()
    assert [c["id"] for c in listed] == [mine]

    stranger = client.get("/api/v1/campaigns", headers=auth(issuer, "stranger"))
    assert stranger.status_code == 200
    assert stranger.json() == []


def test_join_grants_player_or_spectator_relation_by_role(
    client: TestClient, issuer: SigningTestIssuer, spicedb: MockSpiceDBClient
) -> None:
    campaign_id = create_campaign(client, issuer)
    player_token = create_invite(client, issuer, campaign_id, {"role": "player"})
    spectator_token = create_invite(client, issuer, campaign_id, {"role": "spectator"})

    assert join(client, issuer, player_token, "player-marcus").status_code == 200
    assert join(client, issuer, spectator_token, "watcher-sam").status_code == 200

    async def can(user: str, permission: str) -> bool:
        return await spicedb.check_permission("campaign", campaign_id, permission, "user", user)

    assert asyncio.run(can("player-marcus", "play")) is True
    assert asyncio.run(can("watcher-sam", "play")) is False
    assert asyncio.run(can("watcher-sam", "view")) is True


def test_failed_membership_save_writes_no_spicedb_tuple(
    issuer: SigningTestIssuer,
    spicedb: MockSpiceDBClient,
    repos: CampaignRepositories,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(
        session_app,
        headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"},
        raise_server_exceptions=False,
    )
    campaign_id = create_campaign(client, issuer)
    token = create_invite(client, issuer, campaign_id)

    async def failing_save(_aggregate: object) -> None:
        raise RuntimeError("event store unavailable")

    monkeypatch.setattr(repos.memberships, "save", failing_save)

    res = join(client, issuer, token, "player-marcus")
    assert res.status_code == 500

    granted = asyncio.run(
        spicedb.check_permission("campaign", campaign_id, "play", "user", "player-marcus")
    )
    assert granted is False


def test_non_manager_cannot_edit_campaign_or_issue_invites(
    client: TestClient, issuer: SigningTestIssuer
) -> None:
    campaign_id = create_campaign(client, issuer)
    token = create_invite(client, issuer, campaign_id)
    assert join(client, issuer, token, "player-marcus").status_code == 200

    edit = client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={"title": "Hijacked"},
        headers=auth(issuer, "player-marcus"),
    )
    assert edit.status_code == 403
    assert edit.json()["detail"]["error"] == "permission_denied"

    invite = client.post(
        f"/api/v1/campaigns/{campaign_id}/invites",
        json={"role": "player"},
        headers=auth(issuer, "player-marcus"),
    )
    assert invite.status_code == 403


def test_owner_can_update_campaign_title(client: TestClient, issuer: SigningTestIssuer) -> None:
    campaign_id = create_campaign(client, issuer)
    res = client.patch(
        f"/api/v1/campaigns/{campaign_id}",
        json={"title": "Shadows of Drakkenheim, Part II"},
        headers=auth(issuer, "dm-evelyn"),
    )
    assert res.status_code == 200
    assert res.json()["title"] == "Shadows of Drakkenheim, Part II"


def test_owner_cannot_be_removed_from_own_campaign(
    client: TestClient, issuer: SigningTestIssuer
) -> None:
    campaign_id = create_campaign(client, issuer)
    res = client.delete(
        f"/api/v1/campaigns/{campaign_id}/members/dm-evelyn",
        headers=auth(issuer, "dm-evelyn"),
    )
    assert res.status_code == 409
    assert res.json()["detail"]["error"] == "owner_not_removable"


def test_create_session_adds_session_to_campaign_and_spicedb(
    client: TestClient, issuer: SigningTestIssuer, spicedb: MockSpiceDBClient
) -> None:
    campaign_id = create_campaign(client, issuer)
    res = client.post(
        f"/api/v1/campaigns/{campaign_id}/sessions",
        json={"title": "Session #2: Crypt", "status": "scheduled"},
        headers=auth(issuer, "dm-evelyn"),
    )
    assert res.status_code == 201
    session = res.json()
    assert session["campaign_id"] == campaign_id
    assert session["title"] == "Session #2: Crypt"

    titles = [
        s["title"]
        for s in client.get(
            f"/api/v1/campaigns/{campaign_id}/sessions", headers=auth(issuer, "dm-evelyn")
        ).json()
    ]
    assert titles == ["Session #1: Staging Lobby", "Session #2: Crypt"]

    linked = asyncio.run(
        spicedb.read_relationships(resource_type="session", resource_id=session["id"])
    )
    assert [(r.relation, r.subject_id) for r in linked] == [("campaign", campaign_id)]


def test_campaign_routes_reject_missing_or_forged_tokens(
    client: TestClient, issuer: SigningTestIssuer
) -> None:
    rogue = SigningTestIssuer()
    forged = {"Authorization": f"Bearer {rogue.mint('dm-evelyn')}"}

    assert client.get("/api/v1/campaigns").status_code == 401
    assert client.get("/api/v1/campaigns", headers=forged).status_code == 401
    assert client.post("/api/v1/campaigns", json={"title": "x"}, headers=forged).status_code == 401


def test_campaign_routes_are_in_openapi_schema(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/campaigns" in paths
    assert "/api/v1/campaigns/{campaign_id}" in paths
    assert "/api/v1/campaigns/{campaign_id}/invites" in paths
    assert "/api/v1/campaigns/join" in paths
    assert "/api/v1/campaigns/{campaign_id}/members" in paths
    assert "/api/v1/campaigns/{campaign_id}/members/{user_id}" in paths
    assert "/api/v1/campaigns/{campaign_id}/sessions" in paths


@pytest.mark.asyncio
async def test_campaign_membership_and_invites_survive_restart_on_postgres(
    postgres_service: dict[str, Any],
    issuer: SigningTestIssuer,
    spicedb: MockSpiceDBClient,
) -> None:
    """A new process on the same PostgreSQL event store reads the same campaign state."""

    dsn = str(postgres_service["dsn"])

    def bind_process() -> CampaignRepositories:
        settings = PlatformSettings(database_url=dsn, event_store_backend="postgresql")
        set_event_store(build_event_store(settings))
        repos = build_campaign_repositories()
        set_campaign_repositories(repos)
        return repos

    bind_process()
    with TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    ) as first:
        campaign_id = create_campaign(first, issuer, owner="dm-pg-evelyn")
        token = create_invite(first, issuer, campaign_id, owner="dm-pg-evelyn")
        assert join(first, issuer, token, "player-pg-marcus").status_code == 200
    await get_event_store().close()

    bind_process()
    with TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    ) as second:
        got = second.get(f"/api/v1/campaigns/{campaign_id}", headers=auth(issuer, "dm-pg-evelyn"))
        assert got.status_code == 200
        members = second.get(
            f"/api/v1/campaigns/{campaign_id}/members", headers=auth(issuer, "dm-pg-evelyn")
        ).json()
        assert {(m["user_id"], m["role"]) for m in members} == {
            ("dm-pg-evelyn", "owner"),
            ("player-pg-marcus", "player"),
        }
        rejoin = join(second, issuer, token, "player-pg-marcus")
        assert rejoin.status_code == 200
    await get_event_store().close()
