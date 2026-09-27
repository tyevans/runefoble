"""Blackbox TDD tests for Campaign Analytics Telemetry Dashboard UI.

Governed by:
- ADR-0004: Lit Web Components and Storybook UI
- ADR-0013: Microfrontend Architecture and Service Component Vendoring
- Hard Invariant 6: File length limit (< 500 lines, target < 140 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from campaign_analytics.worker import CampaignAnalyticsWorker
from fastapi.testclient import TestClient
from runefoble_events.events import (
    CharacterHealthChanged,
    CombatEncounterStarted,
    CombatRoundAdvanced,
    SessionCreated,
    SessionStarted,
)
from runefoble_platform.redis_bus import RedisStreamsEventBus

from tests.test_blackbox_campaign_analytics_ui.conftest import REPO_ROOT


def test_campaign_analytics_manifest_endpoint(client: TestClient) -> None:
    """Verify GET /ui/manifest frontdoor exposes correct microfrontend metadata."""
    resp = client.get("/ui/manifest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "campaign-analytics"
    assert data["package"] == "@runefoble/campaign-analytics-ui"
    assert data["version"] == "0.1.0"
    assert "runefoble-campaign-analytics" in data["components"]


def test_manifest_and_app_shell_forwarding() -> None:
    """Verify manifest.json on disk and frontend app shell forwarding export."""
    manifest_path = REPO_ROOT / "services/campaign_analytics/ui/manifest.json"
    assert manifest_path.is_file()
    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data["service"] == "campaign-analytics"
    assert "runefoble-campaign-analytics" in manifest_data["components"]

    forwarding_file = REPO_ROOT / "frontend/src/components/runefoble-campaign-analytics.ts"
    assert forwarding_file.is_file()
    assert "@runefoble/campaign-analytics-ui" in forwarding_file.read_text(encoding="utf-8")


def test_typescript_element_source_and_storybook() -> None:
    """Verify TypeScript component decorator and Storybook test scenario states."""
    ui_dir = REPO_ROOT / "services/campaign_analytics/ui"
    comp_file = ui_dir / "src/runefoble-campaign-analytics.ts"
    assert comp_file.is_file()
    comp_src = comp_file.read_text(encoding="utf-8")
    assert "@customElement('runefoble-campaign-analytics')" in comp_src

    stories_file = ui_dir / "src/runefoble-campaign-analytics.stories.ts"
    assert stories_file.is_file()
    stories_content = stories_file.read_text(encoding="utf-8")
    for state in ["EmptyState", "ActiveCombatTelemetry", "VictoryCelebration", "TotalPartyKill"]:
        assert state in stories_content


@pytest.mark.asyncio
async def test_telemetry_dashboard_mvp_turn_metrics(
    client: TestClient,
    event_bus: RedisStreamsEventBus,
    worker: CampaignAnalyticsWorker,
) -> None:
    """Verify frontdoor MVP statistics delivery matching dashboard bindings."""
    campaign_id, session_id, char_id = str(uuid4()), str(uuid4()), str(uuid4())
    await worker.setup_groups()

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
        CombatRoundAdvanced(
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
    await worker.process_once(count=10)

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
