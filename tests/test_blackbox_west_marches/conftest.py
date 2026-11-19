"""Shared fixtures and harness for West Marches blackbox test suite.

Governed by ADR-0001, ADR-0006, and Hard Invariant 7.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from game_session.main import app as session_app
from runefoble_auth.spicedb import MockSpiceDBClient

from tests.helpers.campaign_setup import create_campaign, invite_and_join
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def client(spicedb: MockSpiceDBClient) -> TestClient:
    return TestClient(
        session_app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"}
    )


def _auth(sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.fixture
def party_ids(client: TestClient) -> dict[str, str]:
    """Create two party campaigns through public routes. The officer owns both (registration
    needs campaign ownership). Each player joins its own campaign through an invite."""
    officer, blue, gold = "rowan_officer", "blue_explorer", "gold_scout"
    ids = {"officer": officer, "blue_player": blue, "gold_player": gold}
    for key, player in (("campaign_blue", blue), ("campaign_gold", gold)):
        cid = create_campaign(client, officer, title=key)
        invite_and_join(client, cid, officer, player)
        ids[key] = cid
    return ids
