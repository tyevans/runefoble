"""Blackbox TDD tests for Campaign Chronicle Milestone Timeline UI.

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines, target < 140 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_events.events import (
    AbsenteeRecapGenerated,
    SessionCreated,
    SessionEnded,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.campaign_analytics_service import wait_until


async def grant_view(spicedb_client: MockSpiceDBClient, campaign_id: str) -> None:
    """Give the signed-in test member view rights on a campaign.

    campaign_analytics has no public campaign-creation frontdoor, so the view relation is
    seeded in the authorization double. Tests that assert deny paths do not call this.
    """
    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="view",
        subject_type="user",
        subject_id="user-test",
    )


@pytest.mark.asyncio
async def test_chronicle_timeline_frontdoor_and_recap_metadata(
    spicedb_client: MockSpiceDBClient,
    client: TestClient,
    event_bus: RedisStreamsEventBus,
) -> None:
    """Verify chronicle timeline delivers historical memory recaps and milestone metadata."""
    campaign_id, session_id = str(uuid4()), str(uuid4())
    await grant_view(spicedb_client, campaign_id)

    await event_bus.publish_event(
        "runefoble.events.session",
        SessionCreated(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            title="The Vault of the Dragon Priest",
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.watcher",
        AbsenteeRecapGenerated(
            aggregate_id=uuid4(),
            session_id=session_id,
            character_id="char-sarah",
            character_name="Sarah Cleric",
            stand_in_persona="Brave Guardian",
            narrative_summary="Valeros held off the undead tide while the party searched for the altar.",
            highlights=["Stabilized fallen ally", "Banished undead"],
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionEnded(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            summary="Party successfully cleared the Catacombs.",
        ),
    )
    assert wait_until(
        lambda: (
            client.get(f"/api/v1/analytics/campaigns/{campaign_id}/timeline").json()[
                "total_milestones"
            ]
            >= 2
        )
    )

    resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    assert timeline["campaign_id"] == campaign_id
    assert timeline["total_milestones"] >= 3

    types = [m["type"] for m in timeline["milestones"]]
    assert "session_start" in types
    assert "session_end" in types
    assert "recap" in types

    recap_m = next(m for m in timeline["milestones"] if m["type"] == "recap")
    assert recap_m["metadata"]["character_name"] == "Sarah Cleric"
    assert "Sarah Cleric" in recap_m["title"]


@pytest.mark.asyncio
async def test_chronicle_timeline_pagination_and_filtering(
    spicedb_client: MockSpiceDBClient,
    client: TestClient,
    event_bus: RedisStreamsEventBus,
) -> None:
    """Verify chronicle timeline pagination limits and session query filtering."""
    campaign_id, session_1, session_2 = str(uuid4()), str(uuid4()), str(uuid4())
    await grant_view(spicedb_client, campaign_id)

    await event_bus.publish_event(
        "runefoble.events.session",
        SessionCreated(
            aggregate_id=session_1,
            session_id=session_1,
            campaign_id=campaign_id,
            title="Chapter 1: The Dark Gate",
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionCreated(
            aggregate_id=session_2,
            session_id=session_2,
            campaign_id=campaign_id,
            title="Chapter 2: The Sunken City",
        ),
    )
    assert wait_until(
        lambda: (
            client.get(f"/api/v1/analytics/campaigns/{campaign_id}/timeline").json()[
                "total_milestones"
            ]
            >= 2
        )
    )

    limit_resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/timeline?limit=1")
    assert limit_resp.status_code == 200
    data = limit_resp.json()
    assert len(data["milestones"]) == 1
    assert data["total_milestones"] >= 2

    filter_resp = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/timeline?session_id={session_1}"
    )
    assert filter_resp.status_code == 200
    filtered = filter_resp.json()
    assert all(m["session_id"] == session_1 for m in filtered["milestones"])
