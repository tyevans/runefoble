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
from campaign_analytics.storage import CampaignAnalyticsStorage
from campaign_analytics.worker import CampaignAnalyticsWorker
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

from tests.test_blackbox_campaign_analytics_ui.conftest import REPO_ROOT


def test_spatial_heatmap_custom_element_declaration() -> None:
    """Verify Combat Heatmap Custom Element decorator and Lit component export."""
    heatmap_file = REPO_ROOT / "services/campaign_analytics/ui/src/runefoble-combat-heatmap.ts"
    assert heatmap_file.is_file()
    src = heatmap_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-combat-heatmap')" in src
    assert "class RunefobleCombatHeatmap" in src


def test_combat_heatmap_modular_decomposition_and_limits() -> None:
    """Verify TASK-0194 modular decomposition file boundaries and line limits."""
    ui_src = REPO_ROOT / "services/campaign_analytics/ui/src"
    heatmap_dir = ui_src / "heatmap"

    controller = ui_src / "runefoble-combat-heatmap.ts"
    canvas_renderer = heatmap_dir / "canvas-renderer.ts"
    controls = heatmap_dir / "heatmap-controls.template.ts"
    inspector = heatmap_dir / "cell-inspector.template.ts"

    for path in (controller, canvas_renderer, controls, inspector):
        assert path.is_file(), f"Expected module {path} to exist"

    controller_lines = len(controller.read_text(encoding="utf-8").splitlines())
    canvas_lines = len(canvas_renderer.read_text(encoding="utf-8").splitlines())
    controls_lines = len(controls.read_text(encoding="utf-8").splitlines())
    inspector_lines = len(inspector.read_text(encoding="utf-8").splitlines())

    assert controller_lines < 120, f"controller has {controller_lines} lines, expected < 120"
    assert canvas_lines < 120, f"canvas-renderer has {canvas_lines} lines, expected < 120"
    assert controls_lines < 90, f"controls template has {controls_lines} lines, expected < 90"
    assert inspector_lines < 80, (
        f"cell-inspector template has {inspector_lines} lines, expected < 80"
    )

    # Verify key exports
    assert "renderHeatmapCanvas" in canvas_renderer.read_text(encoding="utf-8")
    assert "renderHeatmapHeader" in controls.read_text(encoding="utf-8")
    assert "renderHeatmapLegend" in controls.read_text(encoding="utf-8")
    assert "renderCellInspector" in inspector.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_spatial_heatmap_frontdoor_cells_and_filtering(
    client: TestClient,
    event_bus: RedisStreamsEventBus,
    worker: CampaignAnalyticsWorker,
) -> None:
    """Verify spatial coordinate density aggregation and filter controls."""
    campaign_id, session_id, char_id = str(uuid4()), str(uuid4()), str(uuid4())
    await worker.setup_groups()

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

    await worker.process_once(count=10)

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
    storage: CampaignAnalyticsStorage,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify SpiceDB Zanzibar object authorization protects telemetry endpoints."""
    campaign_id = "camp-secure-999"

    resp_anon = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/heatmap")
    assert resp_anon.status_code == 200

    resp_unauth = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/heatmap",
        headers={"X-User-ID": "lurker-intruder"},
    )
    assert resp_unauth.status_code == 403
    assert "Forbidden" in resp_unauth.json()["detail"]

    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="view",
        subject_type="user",
        subject_id="authorized-player",
    )

    resp_auth = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/heatmap",
        headers={"X-User-ID": "authorized-player"},
    )
    assert resp_auth.status_code == 200
