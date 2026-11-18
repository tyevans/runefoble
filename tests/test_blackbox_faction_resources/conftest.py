"""Shared test harness and fixtures for Faction Resources and Bribery blackbox tests.

Governed by ADR-0003, ADR-0006, ADR-0007, ADR-0011, and Hard Invariant 7 (Blackbox TDD).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from eventsource.adapters.memory.bus import InMemoryEventBus
from fastapi.testclient import TestClient
from runefoble_auth.factory import get_spicedb_client
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    InMemoryEventStore,
)
from the_watcher.dependencies import get_faction_resource_repo, set_faction_resource_repo
from the_watcher.factions.resources.aggregate import FactionResourceAggregate
from the_watcher.main import app

from tests.helpers.module_state import SeamRestorer
from tests.helpers.ws_identity import SIGNING_ISSUER

pytestmark = pytest.mark.usefixtures("trusted_ws_issuer")


@pytest.fixture(autouse=True)
def clean_resource_environment(seam_restorer: SeamRestorer):
    """Give each test a fresh faction resource repo. The harness sets the bus and SpiceDB."""
    test_store = InMemoryEventStore()
    test_bus = InMemoryEventBus()
    repo = AggregateRepository(
        event_store=test_store,
        aggregate_factory=FactionResourceAggregate,
        event_publisher=test_bus,
    )
    seam_restorer.replace(get_faction_resource_repo, set_faction_resource_repo, repo)
    yield


@pytest.fixture
def client() -> TestClient:
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
