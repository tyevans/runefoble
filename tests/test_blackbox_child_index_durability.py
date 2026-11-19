"""Blackbox durability test for game session list queries under a store outage (TASK-0567).

Governed by ADR-0011 (eventsource-py), ADR-0015 (decisions a, f), and Hard Invariant 7.

The restart tests live in test_blackbox_child_index_restart.py and run each process as a
subprocess. This test has no restart. It stops the event store read on the in-process app,
and the list path must answer 503, never an empty list. Setup uses only public HTTP routes.
"""

from __future__ import annotations

from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from runefoble_auth.mock import MockSpiceDBClient
from runefoble_platform.event_sourcing import get_event_store

from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


def _headers(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def session_client() -> Iterator[TestClient]:
    with TestClient(session_app) as client:
        yield client


async def _grant_session_play(spicedb: MockSpiceDBClient, session_id: str, user: str) -> None:
    """Make the user a campaign player and link the session to that campaign (schema relations)."""
    campaign_id = str(uuid4())
    await spicedb.write_relationship("campaign", campaign_id, "player", "user", user)
    await spicedb.write_relationship("session", session_id, "campaign", "campaign", campaign_id)


@pytest.mark.asyncio
async def test_bounty_list_answers_503_when_the_store_is_unreachable(
    session_client: TestClient,
    spicedb: MockSpiceDBClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A store outage on the list path answers 503. It never returns an empty list."""
    session_id, poster = str(uuid4()), f"poster_{uuid4().hex[:8]}"
    await _grant_session_play(spicedb, session_id, poster)

    def _unreachable(*_args: object, **_kwargs: object) -> None:
        raise ConnectionError("event store unreachable")

    monkeypatch.setattr(get_event_store(), "read_stream", _unreachable)

    listed = session_client.get(
        f"/sessions/{session_id}/contracts/bounties", headers=_headers(poster)
    )
    assert listed.status_code == 503, listed.text
