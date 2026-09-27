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
from campaign_analytics.worker import CampaignAnalyticsWorker
from fastapi.testclient import TestClient
from runefoble_events.events import (
    AbsenteeRecapGenerated,
    SessionCreated,
    SessionEnded,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.test_blackbox_campaign_analytics_ui.conftest import REPO_ROOT


def test_chronicle_timeline_custom_element_declaration() -> None:
    """Verify Chronicle Timeline Custom Element decorator and Lit component export."""
    timeline_file = REPO_ROOT / "services/campaign_analytics/ui/src/runefoble-chronicle-timeline.ts"
    assert timeline_file.is_file()
    src = timeline_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-chronicle-timeline')" in src
    assert "class RunefobleChronicleTimeline" in src


@pytest.mark.asyncio
async def test_chronicle_timeline_frontdoor_and_recap_metadata(
    client: TestClient,
    event_bus: RedisStreamsEventBus,
    worker: CampaignAnalyticsWorker,
) -> None:
    """Verify chronicle timeline delivers historical memory recaps and milestone metadata."""
    campaign_id, session_id = str(uuid4()), str(uuid4())
    await worker.setup_groups()

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
    await worker.process_once(count=10)

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
    client: TestClient,
    event_bus: RedisStreamsEventBus,
    worker: CampaignAnalyticsWorker,
) -> None:
    """Verify chronicle timeline pagination limits and session query filtering."""
    campaign_id, session_1, session_2 = str(uuid4()), str(uuid4()), str(uuid4())
    await worker.setup_groups()

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
    await worker.process_once(count=5)

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
