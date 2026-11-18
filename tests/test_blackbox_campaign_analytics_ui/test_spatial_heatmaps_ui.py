"""Blackbox TDD tests for Campaign Tactical Spatial Damage Heatmaps UI.

Governed by:
- ADR-0001: Fine-Grained Authorization with SpiceDB Zanzibar
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines, target < 140 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from campaign_analytics.main import app
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_events.events import (
    CharacterHealthChanged,
    SessionCreated,
    SessionStarted,
    TokenMoved,
    TokenPlaced,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.helpers.polling import wait_until
from tests.helpers.ws_identity import SIGNING_ISSUER


async def grant_view(spicedb_client: MockSpiceDBClient, campaign_id: str) -> None:
    """Give the signed-in test member view rights on a campaign.

    campaign_analytics has no public campaign-creation frontdoor, so the spectator relation
    (which grants campaign.view) is seeded in the authorization double. Tests that assert deny paths do not call this.
    """
    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="spectator",
        subject_type="user",
        subject_id="user-test",
    )


def bearer(sub: str) -> dict[str, str]:
    """Return the Authorization header for a token that the shared test issuer signs for `sub`."""
    return {"Authorization": f"Bearer {SIGNING_ISSUER.mint(sub)}"}


@pytest.mark.asyncio
async def test_spatial_heatmap_frontdoor_cells_and_filtering(
    spicedb_client: MockSpiceDBClient,
    client: TestClient,
    event_bus: RedisStreamsEventBus,
) -> None:
    """Verify spatial coordinate density aggregation and filter controls."""
    campaign_id, session_id, char_id = str(uuid4()), str(uuid4()), str(uuid4())
    await grant_view(spicedb_client, campaign_id)

    await event_bus.publish_event(
        "runefoble.events.session",
        SessionCreated(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            title="Catacombs",
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionStarted(aggregate_id=session_id, session_id=session_id, campaign_id=campaign_id),
    )
    await event_bus.publish_event(
        "runefoble.events.board",
        TokenPlaced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            token_id=char_id,
            name="Valeros",
            token_type="pc",
            x=3,
            y=3,
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.board",
        TokenMoved(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            token_id=char_id,
            name="Valeros",
            from_x=3,
            from_y=3,
            to_x=4,
            to_y=4,
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
            source="Trap",
        ),
    )

    assert wait_until(
        lambda: (
            client.get(f"/api/v1/analytics/campaigns/{campaign_id}/heatmap").json()["total_points"]
            == 3
        ),
        timeout_s=10.0,
    )

    resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/heatmap?cell_size=5&metric=all")
    assert resp.status_code == 200
    heatmap = resp.json()
    assert heatmap["campaign_id"] == campaign_id
    assert heatmap["total_points"] >= 1
    cell = heatmap["cells"][0]
    assert "x" in cell and "y" in cell
    assert "density" in cell and "damage_total" in cell
    assert "hit_count" in cell and "movement_count" in cell

    metric_resp = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/heatmap?cell_size=10&metric=damage"
    )
    assert metric_resp.status_code == 200
    assert metric_resp.json()["cell_size"] == 10


@pytest.mark.asyncio
async def test_spatial_heatmap_spicedb_zanzibar_authorization(
    client: TestClient,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify SpiceDB Zanzibar object authorization protects telemetry endpoints."""
    campaign_id = "camp-secure-999"

    anonymous = TestClient(app)
    resp_anon = anonymous.get(f"/api/v1/analytics/campaigns/{campaign_id}/heatmap")
    assert resp_anon.status_code == 401

    resp_unauth = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/heatmap",
        headers=bearer("lurker-intruder"),
    )
    assert resp_unauth.status_code == 403
    assert "Forbidden" in resp_unauth.json()["detail"]

    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="spectator",
        subject_type="user",
        subject_id="authorized-player",
    )

    resp_auth = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/heatmap",
        headers=bearer("authorized-player"),
    )
    assert resp_auth.status_code == 200
