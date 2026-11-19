"""Shared test harness and fixtures for Faction Resources and Bribery blackbox tests.

Governed by ADR-0003, ADR-0006, ADR-0007, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client

from tests.helpers.the_watcher_app import app_with_container, fresh_store_container
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture
def app() -> FastAPI:
    """Give each test an app over a fresh event store. The harness sets the bus and SpiceDB."""
    return app_with_container(fresh_store_container())


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, headers={"Authorization": f"Bearer {SIGNING_ISSUER.mint('test-user')}"})


async def setup_campaign_roles(
    dm_user: str = "dm_evelyn", player_user: str = "player_valeros"
) -> tuple[str, str, str]:
    """Helper to seed SpiceDB Zanzibar roles on a campaign."""
    camp_id = str(uuid4())
    spicedb = get_spicedb_client()
    for rel, user in [("dungeon_master", dm_user), ("player", player_user)]:
        await spicedb.write_relationship(
            resource_type="campaign",
            resource_id=camp_id,
            relation=rel,
            subject_type="user",
            subject_id=user,
        )
    return camp_id, dm_user, player_user
