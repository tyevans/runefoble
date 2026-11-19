"""Blackbox tests: the campaign list reads SpiceDB a fixed number of times (TASK-0907).

`GET /api/v1/campaigns` must not do one SpiceDB round trip per campaign. A DM with many
campaigns otherwise passes the gateway timeout. The SpiceDB double counts the calls that
cross the SpiceDB process boundary. Setup goes through public routes only (create, invite,
join). Governed by ADR-0001 and ADR-0014.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_auth.mock.client import MockSpiceDBClient

from tests.helpers.spicedb_factory import shared_spicedb_client

_READS = ("check_permission", "lookup_resources")


class CountingSpiceDB:
    """A SpiceDB double that counts each read call that a service sends to it."""

    def __init__(self, store: MockSpiceDBClient) -> None:
        self._store = store
        self.calls: Counter[str] = Counter()

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._store, name)
        if name not in _READS:
            return target

        async def counted(*args: Any, **kwargs: Any) -> Any:
            self.calls[name] += 1
            return await target(*args, **kwargs)

        return counted

    def reads(self) -> int:
        return sum(self.calls.values())


@pytest.fixture
def counting_spicedb(spicedb: MockSpiceDBClient) -> Iterator[CountingSpiceDB]:
    counting = CountingSpiceDB(spicedb)
    with shared_spicedb_client(counting):
        yield counting


@pytest.fixture
def client(
    counting_spicedb: CountingSpiceDB, game_session_upstream: str, character_sheet_upstream: str
) -> Iterator[TestClient]:
    with TestClient(gateway_app) as gateway_client:
        yield gateway_client


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _create(client: TestClient, headers: dict[str, str], title: str) -> str:
    created = client.post(
        "/api/v1/campaigns",
        json={"title": title, "seed_initial_session": False},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _join(client: TestClient, owner: dict, member: dict, cid: str, role: str) -> None:
    invite = client.post(f"/api/v1/campaigns/{cid}/invites", json={"role": role}, headers=owner)
    assert invite.status_code == 201, invite.text
    joined = client.post(
        "/api/v1/campaigns/join", json={"invite_token": invite.json()["token"]}, headers=member
    )
    assert joined.status_code == 200, joined.text


def _list_reads(client: TestClient, spicedb: CountingSpiceDB, headers: dict) -> tuple[list, int]:
    spicedb.calls.clear()
    listed = client.get("/api/v1/campaigns", headers=headers)
    assert listed.status_code == 200, listed.text
    return listed.json(), spicedb.reads()


def test_list_of_25_campaigns_has_correct_roles_and_flags(client, trusted_ws_issuer) -> None:
    owner = _auth(trusted_ws_issuer, "dm-many")
    player = _auth(trusted_ws_issuer, "player-some")
    ids = [_create(client, owner, f"Campaign {n}") for n in range(25)]
    _join(client, owner, player, ids[3], "player")
    _join(client, owner, player, ids[7], "spectator")

    dm_list = client.get("/api/v1/campaigns", headers=owner)
    assert dm_list.status_code == 200, dm_list.text
    entries = {c["id"]: c for c in dm_list.json()}
    assert set(entries) == set(ids)
    assert all(c["role"] == "owner" for c in entries.values())
    assert all(all(c["permissions"].values()) for c in entries.values())
    assert entries[ids[3]]["member_count"] == 2
    assert entries[ids[0]]["member_count"] == 1

    player_list = client.get("/api/v1/campaigns", headers=player)
    assert player_list.status_code == 200, player_list.text
    seen = {c["id"]: c for c in player_list.json()}
    assert set(seen) == {ids[3], ids[7]}
    assert seen[ids[3]]["role"] == "player"
    assert seen[ids[7]]["role"] == "spectator"
    for entry in seen.values():
        flags = entry["permissions"]
        assert flags["view"] is True
        assert not (flags["manage"] or flags["invite"] or flags["launch_session"])
        assert flags["assign_roles"] is False


def test_spicedb_reads_do_not_grow_with_the_campaign_count(
    client, counting_spicedb: CountingSpiceDB, trusted_ws_issuer
) -> None:
    owner = _auth(trusted_ws_issuer, "dm-growth")
    _create(client, owner, "First")
    listed, reads_for_one = _list_reads(client, counting_spicedb, owner)
    assert len(listed) == 1

    for n in range(24):
        _create(client, owner, f"More {n}")
    listed, reads_for_25 = _list_reads(client, counting_spicedb, owner)

    assert len(listed) == 25
    assert reads_for_25 == reads_for_one
    assert counting_spicedb.calls["check_permission"] == 0


def test_caller_with_no_campaigns_gets_an_empty_list(client, trusted_ws_issuer) -> None:
    listed = client.get("/api/v1/campaigns", headers=_auth(trusted_ws_issuer, "nobody"))
    assert listed.status_code == 200, listed.text
    assert listed.json() == []


def test_campaigns_are_listed_oldest_first(client, trusted_ws_issuer) -> None:
    """The list order is the creation order, not the order of the random campaign ids."""
    owner = _auth(trusted_ws_issuer, "dm-order")
    ids = [_create(client, owner, f"Ordered {n}") for n in range(6)]

    listed = client.get("/api/v1/campaigns", headers=owner)
    assert listed.status_code == 200, listed.text
    assert [c["id"] for c in listed.json()] == ids
