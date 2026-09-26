"""Blackbox TDD frontdoor test suite for Campaign Analytics UI Microfrontend.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0007: Real-Time Voice and Board Synchronization
- ADR-0011: eventsource-py Core Event Sourcing
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from campaign_analytics.dependencies import set_spicedb_client, set_storage, set_worker
from campaign_analytics.main import app
from campaign_analytics.storage import CampaignAnalyticsStorage
from campaign_analytics.worker import CampaignAnalyticsWorker
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_events.events import (
    AbsenteeRecapGenerated,
    CharacterHealthChanged,
    CombatEncounterStarted,
    CombatRoundAdvanced,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    TokenMoved,
    TokenPlaced,
)
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def mock_redis() -> MockAsyncRedis:
    return MockAsyncRedis()


@pytest.fixture
def consumer_group(mock_redis: MockAsyncRedis) -> RedisConsumerGroup:
    return RedisConsumerGroup(client=mock_redis)


@pytest.fixture
def event_bus(mock_redis: MockAsyncRedis) -> RedisStreamsEventBus:
    return RedisStreamsEventBus(client=mock_redis)


@pytest.fixture
def storage() -> CampaignAnalyticsStorage:
    return CampaignAnalyticsStorage()


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    return MockSpiceDBClient()


@pytest.fixture
def worker(
    storage: CampaignAnalyticsStorage, consumer_group: RedisConsumerGroup
) -> CampaignAnalyticsWorker:
    return CampaignAnalyticsWorker(
        storage=storage,
        consumer_group=consumer_group,
        group_name="test_ui_analytics_workers",
        consumer_name="test_ui_worker_1",
    )


@pytest.fixture
def client(
    storage: CampaignAnalyticsStorage,
    worker: CampaignAnalyticsWorker,
    spicedb_client: MockSpiceDBClient,
) -> TestClient:
    set_storage(storage)
    set_worker(worker)
    set_spicedb_client(spicedb_client)
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Microfrontend Manifest & File Structure Integrity
# ---------------------------------------------------------------------------


def test_campaign_analytics_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes correct microfrontend metadata."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "campaign-analytics"
    assert data["package"] == "@runefoble/campaign-analytics-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-campaign-analytics" in data["components"]
    assert "runefoble-combat-heatmap" in data["components"]
    assert "runefoble-chronicle-timeline" in data["components"]


def test_manifest_file_matches_advertised_manifest() -> None:
    """Verify services/campaign_analytics/ui/manifest.json matches runtime advertising."""
    manifest_path = REPO_ROOT / "services/campaign_analytics/ui/manifest.json"
    assert manifest_path.is_file(), f"{manifest_path} must exist"

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "campaign-analytics"
    assert manifest_data["package"] == "@runefoble/campaign-analytics-ui"
    assert manifest_data["version"] == "0.1.0"
    assert "runefoble-campaign-analytics" in manifest_data["components"]
    assert "runefoble-combat-heatmap" in manifest_data["components"]
    assert "runefoble-chronicle-timeline" in manifest_data["components"]


def test_typescript_element_source_and_custom_elements() -> None:
    """Verify UI package configuration, exports, and Custom Element decorators."""
    ui_dir = REPO_ROOT / "services/campaign_analytics/ui"

    pkg_json = json.loads((ui_dir / "package.json").read_text(encoding="utf-8"))
    assert pkg_json["name"] == "@runefoble/campaign-analytics-ui"
    assert pkg_json["exports"]["."].endswith("index.ts")

    assert (ui_dir / "tsconfig.json").is_file()
    assert (ui_dir / "src/index.ts").is_file()

    # Check runefoble-campaign-analytics
    comp_file = ui_dir / "src/runefoble-campaign-analytics.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-campaign-analytics')" in comp_src
    assert "class RunefobleCampaignAnalytics" in comp_src

    # Check runefoble-combat-heatmap
    heatmap_file = ui_dir / "src/runefoble-combat-heatmap.ts"
    assert heatmap_file.is_file()
    heatmap_src = heatmap_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-combat-heatmap')" in heatmap_src
    assert "class RunefobleCombatHeatmap" in heatmap_src

    # Check runefoble-chronicle-timeline
    timeline_file = ui_dir / "src/runefoble-chronicle-timeline.ts"
    assert timeline_file.is_file()
    timeline_src = timeline_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-chronicle-timeline')" in timeline_src
    assert "class RunefobleChronicleTimeline" in timeline_src


def test_storybook_stories_definition() -> None:
    """Verify Storybook stories include EmptyState, ActiveCombat, Victory, and TPK scenarios."""
    stories_file = (
        REPO_ROOT / "services/campaign_analytics/ui/src/runefoble-campaign-analytics.stories.ts"
    )
    assert stories_file.is_file()
    content = stories_file.read_text(encoding="utf-8")
    assert "EmptyState" in content
    assert "ActiveCombatTelemetry" in content
    assert "VictoryCelebration" in content
    assert "TotalPartyKill" in content
    assert "runefoble-campaign-analytics" in content


def test_frontend_app_shell_forwarding_export() -> None:
    """Verify frontend/src/components/ re-exports the microfrontend per ADR-0013."""
    forwarding_file = REPO_ROOT / "frontend/src/components/runefoble-campaign-analytics.ts"
    assert forwarding_file.is_file()
    content = forwarding_file.read_text(encoding="utf-8")
    assert "@runefoble/campaign-analytics-ui" in content


# ---------------------------------------------------------------------------
# 2. REST Frontdoor Data Binding Integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rest_data_binding_frontdoors_and_schema(
    client: TestClient,
    event_bus: RedisStreamsEventBus,
    worker: CampaignAnalyticsWorker,
) -> None:
    """Verify REST frontdoor endpoints deliver schemas matching microfrontend data bindings."""
    campaign_id = str(uuid4())
    session_id = str(uuid4())
    char_id = str(uuid4())

    await worker.setup_groups()

    # Frontdoor setup: emit domain events through standard event bus
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
        "runefoble.events.session",
        SessionStarted(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.board",
        TokenPlaced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            token_id=char_id,
            name="Valeros the Fighter",
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
            name="Valeros the Fighter",
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
            source="Ghoul Claws",
        ),
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
        CombatRoundAdvanced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            round_number=1,
            active_combatant_id=char_id,
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.watcher",
        AbsenteeRecapGenerated(
            aggregate_id=uuid4(),
            session_id=str(session_id),
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

    # Process events through worker
    await worker.process_once(count=15)

    # 1. Query Heatmap Endpoint
    h_resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/heatmap")
    assert h_resp.status_code == 200
    heatmap = h_resp.json()
    assert heatmap["campaign_id"] == campaign_id
    assert "cells" in heatmap
    assert isinstance(heatmap["cells"], list)
    assert heatmap["total_points"] >= 1
    # Check cell structure
    cell = heatmap["cells"][0]
    assert "x" in cell and "y" in cell
    assert "density" in cell and "damage_total" in cell
    assert "hit_count" in cell and "movement_count" in cell

    # 2. Query MVP Statistics Endpoint
    m_resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/mvp")
    assert m_resp.status_code == 200
    mvp = m_resp.json()
    assert mvp["campaign_id"] == campaign_id
    assert "combatants" in mvp
    assert isinstance(mvp["combatants"], list)
    assert len(mvp["combatants"]) >= 1
    combatant = mvp["combatants"][0]
    assert combatant["combatant_name"] == "Valeros the Fighter"
    assert combatant["damage_taken"] == 13

    # 3. Query Living Chronicle Timeline Endpoint
    t_resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/timeline")
    assert t_resp.status_code == 200
    timeline = t_resp.json()
    assert timeline["campaign_id"] == campaign_id
    assert timeline["total_milestones"] >= 3
    milestones = timeline["milestones"]
    types = [m["type"] for m in milestones]
    assert "session_start" in types
    assert "session_end" in types
    assert "recap" in types

    recap_m = next(m for m in milestones if m["type"] == "recap")
    assert recap_m["metadata"]["character_name"] == "Sarah Cleric"
    assert "Sarah Cleric" in recap_m["title"]


# ---------------------------------------------------------------------------
# 3. SpiceDB Zanzibar Fine-Grained Authorization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spicedb_zanzibar_authorization_on_ui_endpoints(
    client: TestClient,
    storage: CampaignAnalyticsStorage,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify object authorization prevents unauthorized callers from accessing telemetry."""
    campaign_id = "camp-secure-999"

    # Anonymous call allows public read
    resp_anon = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/heatmap")
    assert resp_anon.status_code == 200

    # Unauthorized caller header -> 403 Forbidden
    resp_unauth = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/heatmap",
        headers={"X-User-ID": "lurker-intruder"},
    )
    assert resp_unauth.status_code == 403
    assert "Forbidden" in resp_unauth.json()["detail"]

    # Grant 'view' permission in Zanzibar
    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="view",
        subject_type="user",
        subject_id="authorized-player",
    )

    # Authorized caller header -> 200 OK
    resp_auth = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/heatmap",
        headers={"X-User-ID": "authorized-player"},
    )
    assert resp_auth.status_code == 200
