"""Blackbox durability tests for game session list queries (TASK-0567).

Governed by ADR-0011 (eventsource-py), ADR-0015 (decisions a, f), and Hard Invariant 7.

A restart is a fresh game session process. The test removes every `game_session` module
from `sys.modules` and imports the app again. The new process has no module-level state.
The event store and the Redis double are shared, as a durable store would be. Setup and
assertions use only public HTTP routes. The store double sits at the store boundary.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.spicedb import MockSpiceDBClient
from runefoble_platform.event_sourcing import get_event_store

from tests.helpers.mock_redis import MockAsyncRedis
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def _is_game_session(name: str) -> bool:
    return name == "game_session" or name.startswith("game_session.")


def _headers(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def isolated_game_session_modules() -> Iterator[None]:
    """Restore the original game session modules after each test."""
    saved = {name: mod for name, mod in sys.modules.items() if _is_game_session(name)}
    yield
    for name in [n for n in sys.modules if _is_game_session(n)]:
        del sys.modules[name]
    sys.modules.update(saved)


@pytest.fixture
def spicedb() -> MockSpiceDBClient:
    return MockSpiceDBClient()


async def _grant_session_play(spicedb: MockSpiceDBClient, session_id: str, user: str) -> None:
    """Make the user a campaign player and link the session to that campaign (schema relations)."""
    campaign_id = str(uuid4())
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", user)
    await spicedb.write_relationship("session", session_id, "campaign", "campaign", campaign_id)


@pytest.fixture
def redis_double() -> MockAsyncRedis:
    return MockAsyncRedis()


def _boot_session_process(
    spicedb: MockSpiceDBClient, redis: MockAsyncRedis, use_redis_client
) -> TestClient:
    """Start a new game session process over the shared event store and Redis double."""
    for name in [n for n in sys.modules if _is_game_session(n)]:
        del sys.modules[name]
    main = importlib.import_module("game_session.main")
    deps = importlib.import_module("game_session.dependencies")
    tokens = importlib.import_module("game_session.settlement.auth.tokens")
    tokens.set_zitadel_auth_service(SIGNING_ISSUER.verifier())
    deps.set_spicedb_client(spicedb)
    use_redis_client(redis)
    return TestClient(main.app)


@pytest.mark.asyncio
async def test_posted_bounty_is_listed_after_restart(
    isolated_game_session_modules: None,
    spicedb: MockSpiceDBClient,
    redis_double: MockAsyncRedis,
) -> None:
    """A bounty posted before a restart still appears in the session bounty list."""
    session_id, poster = str(uuid4()), f"poster_{uuid4().hex[:8]}"
    await _grant_session_play(spicedb, session_id, poster)
    client = _boot_session_process(spicedb, redis_double)
    posted = client.post(
        f"/sessions/{session_id}/contracts/bounties",
        json={
            "title": "Clear the Ash Warrens",
            "description": "Goblin raiders hold the warrens.",
            "target_type": "monster_hunt",
            "target_name": "Goblin Raider",
            "target_quantity": 3,
            "escrow_gold": 120,
            "escrow_items": [],
            "campaign_id": str(uuid4()),
        },
        headers=_headers(poster),
    )
    assert posted.status_code == 201, posted.text
    bounty_id = posted.json()["bounty"]["bounty_id"]

    client = _boot_session_process(spicedb, redis_double)

    listed = client.get(f"/sessions/{session_id}/contracts/bounties", headers=_headers(poster))
    assert listed.status_code == 200, listed.text
    assert [b["bounty_id"] for b in listed.json()["bounties"]] == [bounty_id]


@pytest.mark.asyncio
async def test_founded_settlement_is_listed_after_restart(
    isolated_game_session_modules: None,
    spicedb: MockSpiceDBClient,
    redis_double: MockAsyncRedis,
) -> None:
    """A settlement founded before a restart still appears in the campaign settlement list."""
    cid, founder = str(uuid4()), f"founder_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "player", "user", founder)
    client = _boot_session_process(spicedb, redis_double)
    founded = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Ember Hollow", "scale": "market_town", "districts": ["commons"]},
        headers=_headers(founder),
    )
    assert founded.status_code == 201, founded.text
    settlement_id = founded.json()["settlement_id"]

    client = _boot_session_process(spicedb, redis_double)

    listed = client.get(f"/api/v1/campaigns/{cid}/settlements", headers=_headers(founder))
    assert listed.status_code == 200, listed.text
    assert [s["settlement_id"] for s in listed.json()] == [settlement_id]


@pytest.mark.asyncio
async def test_constructed_establishment_is_listed_after_restart(
    isolated_game_session_modules: None,
    spicedb: MockSpiceDBClient,
    redis_double: MockAsyncRedis,
) -> None:
    """An establishment built before a restart still appears in its settlement list."""
    cid, mayor = str(uuid4()), f"mayor_{uuid4().hex[:8]}"
    await spicedb.write_relationship("campaign", cid, "player", "user", mayor)
    client = _boot_session_process(spicedb, redis_double)
    founded = client.post(
        f"/api/v1/campaigns/{cid}/settlements",
        json={"name": "Glassmere", "scale": "market_town", "districts": ["bazaar"]},
        headers=_headers(mayor),
    )
    settlement_id = founded.json()["settlement_id"]
    built = client.post(
        f"/api/v1/settlements/{settlement_id}/establishments",
        json={
            "district_id": "bazaar",
            "category": "commerce",
            "name": "The Glass Stall",
            "capacity": 10,
            "operating_cost": 2,
        },
        headers=_headers(mayor),
    )
    assert built.status_code == 201, built.text
    establishment_id = built.json()["establishment_id"]

    client = _boot_session_process(spicedb, redis_double)

    listed = client.get(
        f"/api/v1/settlements/{settlement_id}/establishments", headers=_headers(mayor)
    )
    assert listed.status_code == 200, listed.text
    assert [e["establishment_id"] for e in listed.json()] == [establishment_id]


@pytest.mark.asyncio
async def test_bounty_list_answers_503_when_the_store_is_unreachable(
    isolated_game_session_modules: None,
    spicedb: MockSpiceDBClient,
    redis_double: MockAsyncRedis,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A store outage on the list path answers 503. It never returns an empty list."""
    session_id, poster = str(uuid4()), f"poster_{uuid4().hex[:8]}"
    await _grant_session_play(spicedb, session_id, poster)
    client = _boot_session_process(spicedb, redis_double)

    def _unreachable(*_args: object, **_kwargs: object) -> None:
        raise ConnectionError("event store unreachable")

    monkeypatch.setattr(get_event_store(), "read_stream", _unreachable)

    listed = client.get(f"/sessions/{session_id}/contracts/bounties", headers=_headers(poster))
    assert listed.status_code == 503, listed.text
