"""Blackbox TDD tests for Campaign Analytics Telemetry Dashboard UI.

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
    CharacterHealthChanged,
    CombatEncounterStarted,
    InitiativeTurnAdvanced,
    SessionCreated,
    SessionStarted,
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
        relation="spectator",
        subject_type="user",
        subject_id="user-test",
    )


def test_campaign_analytics_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes correct microfrontend metadata."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "campaign-analytics"
    assert data["package"] == "@runefoble/campaign-analytics-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-campaign-analytics" in data["components"]


@pytest.mark.asyncio
async def test_telemetry_dashboard_mvp_turn_metrics(
    spicedb_client: MockSpiceDBClient,
    client: TestClient,
    event_bus: RedisStreamsEventBus,
) -> None:
    """Verify frontdoor MVP statistics delivery matching dashboard bindings."""
    campaign_id, session_id, char_id = str(uuid4()), str(uuid4()), str(uuid4())
    await grant_view(spicedb_client, campaign_id)

    await event_bus.publish_event(
        "runefoble.events.session",
        SessionCreated(
            aggregate_id=session_id, session_id=session_id, campaign_id=campaign_id, title="Vault"
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionStarted(aggregate_id=session_id, session_id=session_id, campaign_id=campaign_id),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        CombatEncounterStarted(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            round_number=1,
            combatants=[],
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        InitiativeTurnAdvanced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            round_number=1,
            active_combatant_id=char_id,
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.character",
        CharacterHealthChanged(
            aggregate_id=char_id,
            session_id=session_id,
            campaign_id=campaign_id,
            current_hp=32,
            max_hp=45,
            delta=-13,
            source="Ghoul Claws",
        ),
    )
    assert wait_until(
        lambda: any(
            c["damage_taken"] == 13
            for c in client.get(f"/api/v1/analytics/campaigns/{campaign_id}/mvp").json()[
                "combatants"
            ]
        )
    )

    resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/mvp")
    assert resp.status_code == 200
    mvp = resp.json()
    assert mvp["campaign_id"] == campaign_id
    assert len(mvp["combatants"]) >= 1
    assert mvp["combatants"][0]["damage_taken"] == 13

    filtered = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/mvp?session_id=nonexistent-session"
    )
    assert filtered.status_code == 200
    assert len(filtered.json()["combatants"]) == 0


@pytest.mark.asyncio
async def test_health_change_without_session_is_not_counted(
    spicedb_client: MockSpiceDBClient,
    client: TestClient,
    event_bus: RedisStreamsEventBus,
) -> None:
    """A health change with a null session id is skipped. It never counts as a character key."""
    campaign_id, session_id, char_id = str(uuid4()), str(uuid4()), str(uuid4())
    await grant_view(spicedb_client, campaign_id)

    await event_bus.publish_event(
        "runefoble.events.session",
        SessionCreated(
            aggregate_id=session_id, session_id=session_id, campaign_id=campaign_id, title="Vault"
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        InitiativeTurnAdvanced(
            aggregate_id=session_id,
            session_id=session_id,
            round_number=1,
            active_combatant_id=char_id,
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.character",
        CharacterHealthChanged(
            aggregate_id=char_id,
            session_id=None,
            campaign_id=campaign_id,
            current_hp=21,
            max_hp=30,
            delta=-9,
            source="Stray Hit",
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.character",
        CharacterHealthChanged(
            aggregate_id=char_id,
            session_id=session_id,
            campaign_id=campaign_id,
            current_hp=8,
            max_hp=30,
            delta=-13,
            source="Ghoul Claws",
        ),
    )
    assert wait_until(
        lambda: any(
            c["damage_taken"] == 13
            for c in client.get(f"/api/v1/analytics/campaigns/{campaign_id}/mvp").json()[
                "combatants"
            ]
        )
    )

    combatants = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/mvp").json()["combatants"]
    assert sum(c["damage_taken"] for c in combatants) == 13
