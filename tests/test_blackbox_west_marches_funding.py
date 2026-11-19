"""Blackbox tests for West Marches outpost funding and the first upgrade (TASK-0795).

An outpost has a funding route. A contributing campaign moves gold from its stronghold
treasury (game_session) into the outpost store (campaign_lore). The debit and the credit
are observable through public routes and the emitted standard events.

Setup goes through public routes. Permissions are schema tuples written to the SpiceDB
test double. game_session runs as a live loopback upstream (ADR-0015 e, Hard Invariant 7).

Governed by ADR-0001, ADR-0011, ADR-0014, and ADR-0015.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from campaign_lore.dependencies import get_west_marches_repo, set_west_marches_repo
from campaign_lore.main import app as lore_app
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from game_session.shared.streams import STREAM_STRONGHOLD
from runefoble_auth.mock import MockSpiceDBClient

from tests.helpers.live_services import closed_port_url
from tests.helpers.module_state import SeamRestorer
from tests.helpers.ws_identity import bearer

DM = "dm_evelyn"
PLAYER = "smith_mira"
LORE_OUTPOST_STREAM = "runefoble.events.lore.outpost_resources_contributed"
TREASURY_EVENT = "runefoble.events.downtime.stronghold_treasury_contributed"
OUTPOST_EVENT = "runefoble.events.west_marches.outpost_resources_contributed"


@pytest.fixture
def lore_client(
    lore_backends,
    spicedb: MockSpiceDBClient,
    game_session_upstream: str,
    seam_restorer: SeamRestorer,
) -> Iterator[TestClient]:
    """Campaign Lore with its production repositories. game_session is its live upstream.

    This fixture clears any repository override for the test, so the events reach the bus
    through the production publisher. The previous repository is restored afterwards.
    Each test uses fresh campaign ids, so the shared event store does not leak state.
    """
    seam_restorer.replace(get_west_marches_repo, set_west_marches_repo, None)
    with TestClient(lore_app) as client:
        yield client


@pytest.fixture
def session_client(trusted_ws_issuer) -> Iterator[TestClient]:
    with TestClient(session_app) as client:
        yield client


async def _funded_campaign(
    session_client: TestClient, spicedb: MockSpiceDBClient, gold: int
) -> str:
    """A DM owns a campaign and deposits gold. A player can play there but cannot manage it."""
    created = session_client.post(
        "/api/v1/campaigns", json={"title": "Frontier Funders"}, headers=bearer(DM)
    )
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]
    deposit = session_client.post(
        f"/api/v1/campaigns/{campaign_id}/stronghold/deposit",
        json={"gold": gold},
        headers=bearer(DM),
    )
    assert deposit.status_code == 200, deposit.text
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", PLAYER)
    return campaign_id


def _treasury(session_client: TestClient, campaign_id: str) -> int:
    res = session_client.get(f"/api/v1/campaigns/{campaign_id}/stronghold", headers=bearer(DM))
    assert res.status_code == 200, res.text
    return res.json()["treasury_gold"]


def _outpost(lore_client: TestClient, campaign_id: str) -> dict:
    res = lore_client.get(f"/api/v1/campaigns/{campaign_id}/west-marches", headers=bearer(PLAYER))
    assert res.status_code == 200, res.text
    return next(iter(res.json()["outposts"].values()))


def _event_types(mock_bus, stream: str) -> list[str]:
    return [entry[1].get("event_type", "") for entry in mock_bus.streams.get(stream, [])]


def _contribute(lore_client: TestClient, campaign_id: str, body: dict, user: str = DM):
    return lore_client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/stronghold/contribute",
        json=body,
        headers=bearer(user),
    )


@pytest.mark.asyncio
async def test_first_upgrade_in_a_fresh_frontier_answers_200(
    lore_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """A frontier with no prior events still has its default outpost. The first upgrade is 200."""
    campaign_id = str(uuid4())
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", PLAYER)

    res = lore_client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/stronghold/upgrade",
        json={"facility_id": "watchtower"},
        headers=bearer(PLAYER),
    )

    assert res.status_code == 200, res.text
    assert res.json()["new_tier"] == 2


@pytest.mark.asyncio
async def test_upgrade_naming_an_unknown_outpost_answers_404_and_changes_nothing(
    lore_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    """An upgrade must not fall back to another outpost. An unknown id answers 404."""
    campaign_id = str(uuid4())
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", PLAYER)
    before = _outpost(lore_client, campaign_id)

    res = lore_client.post(
        f"/api/v1/campaigns/{campaign_id}/west-marches/stronghold/upgrade",
        json={"facility_id": "watchtower", "outpost_id": "outpost_missing"},
        headers=bearer(PLAYER),
    )

    assert res.status_code == 404, res.text
    assert _outpost(lore_client, campaign_id) == before


@pytest.mark.asyncio
async def test_contribution_debits_the_stronghold_and_credits_the_outpost(
    lore_client: TestClient, session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus
) -> None:
    """120 gold leaves the treasury of 300 and joins the outpost store of 100."""
    campaign_id = await _funded_campaign(session_client, spicedb, gold=300)

    res = _contribute(lore_client, campaign_id, {"gold": 120})

    assert res.status_code == 200, res.text
    assert res.json()["gold"] == 120
    assert _treasury(session_client, campaign_id) == 180
    assert _outpost(lore_client, campaign_id)["stored_resources"]["gold"] == 100 + 120
    assert TREASURY_EVENT in _event_types(mock_bus, STREAM_STRONGHOLD)
    assert OUTPOST_EVENT in _event_types(mock_bus, LORE_OUTPOST_STREAM)


@pytest.mark.asyncio
async def test_contribution_shortfall_answers_409_and_emits_no_event(
    lore_client: TestClient, session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus
) -> None:
    """A treasury of 300 cannot fund 500. Both stores keep their values and no event is emitted."""
    campaign_id = await _funded_campaign(session_client, spicedb, gold=300)
    before = _outpost(lore_client, campaign_id)

    res = _contribute(lore_client, campaign_id, {"gold": 500})

    assert res.status_code == 409, res.text
    assert _treasury(session_client, campaign_id) == 300
    assert _outpost(lore_client, campaign_id) == before
    assert TREASURY_EVENT not in _event_types(mock_bus, STREAM_STRONGHOLD)
    assert OUTPOST_EVENT not in _event_types(mock_bus, LORE_OUTPOST_STREAM)


@pytest.mark.asyncio
async def test_contribution_without_stronghold_manage_answers_403(
    lore_client: TestClient, session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus
) -> None:
    """A player may play the frontier but cannot spend the treasury. The debit is refused."""
    campaign_id = await _funded_campaign(session_client, spicedb, gold=300)
    before = _outpost(lore_client, campaign_id)

    res = _contribute(lore_client, campaign_id, {"gold": 50}, user=PLAYER)

    assert res.status_code == 403, res.text
    assert _treasury(session_client, campaign_id) == 300
    assert _outpost(lore_client, campaign_id) == before
    assert TREASURY_EVENT not in _event_types(mock_bus, STREAM_STRONGHOLD)


@pytest.mark.asyncio
async def test_contribution_to_an_unknown_outpost_answers_404_before_any_debit(
    lore_client: TestClient, session_client: TestClient, spicedb: MockSpiceDBClient, mock_bus
) -> None:
    """The outpost is resolved before the treasury is debited."""
    campaign_id = await _funded_campaign(session_client, spicedb, gold=300)

    res = _contribute(lore_client, campaign_id, {"gold": 50, "outpost_id": "outpost_missing"})

    assert res.status_code == 404, res.text
    assert _treasury(session_client, campaign_id) == 300
    assert TREASURY_EVENT not in _event_types(mock_bus, STREAM_STRONGHOLD)


@pytest.mark.asyncio
async def test_contribution_with_game_session_unreachable_answers_503_and_credits_nothing(
    lore_client: TestClient,
    session_client: TestClient,
    spicedb: MockSpiceDBClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A refused connection to game_session is an error. The outpost store is not credited."""
    campaign_id = await _funded_campaign(session_client, spicedb, gold=300)
    before = _outpost(lore_client, campaign_id)
    monkeypatch.setenv("RUNEFOBLE_GAME_SESSION_URL", closed_port_url())

    res = _contribute(lore_client, campaign_id, {"gold": 50})

    assert res.status_code == 503, res.text
    assert _outpost(lore_client, campaign_id) == before


@pytest.mark.asyncio
async def test_contribution_refuses_a_non_positive_amount(
    lore_client: TestClient, session_client: TestClient, spicedb: MockSpiceDBClient
) -> None:
    campaign_id = await _funded_campaign(session_client, spicedb, gold=300)

    res = _contribute(lore_client, campaign_id, {"gold": 0})

    assert res.status_code == 422, res.text
    assert _treasury(session_client, campaign_id) == 300
