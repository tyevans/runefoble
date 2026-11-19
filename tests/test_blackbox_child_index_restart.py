"""Blackbox restart tests for game session list queries (TASK-0567, TASK-0698).

Governed by ADR-0011 (eventsource-py), ADR-0015 (decisions a, f), and Hard Invariant 7.

A restart is a new game session process. Each write goes through a public route in one child
process. The child stops, and a second child reads the list route over the same PostgreSQL
event store, Redis, and SpiceDB. The test process never imports game session modules twice.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import httpx
import pytest

from tests.helpers.restart_stack import RestartStack
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("restart_stack")

# A child that has just started can answer slowly on a loaded machine.
REQUEST_TIMEOUT_SECONDS = 30.0


def _get(url: str, **kwargs: Any) -> httpx.Response:
    return httpx.get(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)


def _post(url: str, **kwargs: Any) -> httpx.Response:
    return httpx.post(url, timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)


GAME_SESSION_APP = "game_session.main:app"


def _headers(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


def test_posted_bounty_is_listed_after_restart(restart_stack: RestartStack) -> None:
    """A bounty posted before a restart still appears in the session bounty list."""
    session_id, poster, campaign_id = str(uuid4()), f"poster_{uuid4().hex[:8]}", str(uuid4())
    restart_stack.grant(
        [
            ("campaign", campaign_id, "player", "user", poster),
            ("game_session", session_id, "campaign", "campaign", campaign_id),
        ]
    )

    with restart_stack.start(GAME_SESSION_APP) as base:
        posted = _post(
            f"{base}/api/v1/sessions/{session_id}/contracts/bounties",
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

    with restart_stack.start(GAME_SESSION_APP) as base:
        listed = _get(
            f"{base}/api/v1/sessions/{session_id}/contracts/bounties", headers=_headers(poster)
        )
    assert listed.status_code == 200, listed.text
    assert [b["bounty_id"] for b in listed.json()["bounties"]] == [bounty_id]


def test_founded_settlement_is_listed_after_restart(restart_stack: RestartStack) -> None:
    """A settlement founded before a restart still appears in the campaign settlement list."""
    cid, founder = str(uuid4()), f"founder_{uuid4().hex[:8]}"
    restart_stack.grant([("campaign", cid, "player", "user", founder)])

    with restart_stack.start(GAME_SESSION_APP) as base:
        founded = _post(
            f"{base}/api/v1/campaigns/{cid}/settlements",
            json={"name": "Ember Hollow", "scale": "market_town", "districts": ["commons"]},
            headers=_headers(founder),
        )
    assert founded.status_code == 201, founded.text
    settlement_id = founded.json()["settlement_id"]

    with restart_stack.start(GAME_SESSION_APP) as base:
        listed = _get(f"{base}/api/v1/campaigns/{cid}/settlements", headers=_headers(founder))
    assert listed.status_code == 200, listed.text
    assert [s["settlement_id"] for s in listed.json()] == [settlement_id]


def test_constructed_establishment_is_listed_after_restart(restart_stack: RestartStack) -> None:
    """An establishment built before a restart still appears in its settlement list."""
    cid, mayor = str(uuid4()), f"mayor_{uuid4().hex[:8]}"
    restart_stack.grant([("campaign", cid, "player", "user", mayor)])

    with restart_stack.start(GAME_SESSION_APP) as base:
        founded = _post(
            f"{base}/api/v1/campaigns/{cid}/settlements",
            json={"name": "Glassmere", "scale": "market_town", "districts": ["bazaar"]},
            headers=_headers(mayor),
        )
        settlement_id = founded.json()["settlement_id"]
        built = _post(
            f"{base}/api/v1/settlements/{settlement_id}/establishments",
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

    with restart_stack.start(GAME_SESSION_APP) as base:
        listed = _get(
            f"{base}/api/v1/settlements/{settlement_id}/establishments", headers=_headers(mayor)
        )
    assert listed.status_code == 200, listed.text
    assert [e["establishment_id"] for e in listed.json()] == [establishment_id]
