"""Blackbox TDD frontdoor test suite for Campaign Analytics & Chronicle Archive.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- ADR-0006: Redis Streams Distributed Event Bus
- ADR-0011: eventsource-py Core Event Sourcing
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 2: DeclarativeAggregate event sourcing
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

import time
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
    DiceRolled,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    TokenMoved,
    TokenPlaced,
)
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup
from runefoble_platform.redis_bus import RedisStreamsEventBus


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
        group_name="test_analytics_workers",
        consumer_name="test_worker_1",
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


def test_service_healthz_and_openapi(client: TestClient) -> None:
    """Verify /healthz, /metrics, and /openapi.json frontdoors."""
    assert client.get("/healthz").json() == {"status": "ok", "service": "campaign-analytics"}
    assert "spatial_records_count" in client.get("/metrics").json()
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/analytics/campaigns/{id}/heatmap" in paths
    assert "/api/v1/analytics/campaigns/{id}/mvp" in paths
    assert "/api/v1/analytics/campaigns/{id}/timeline" in paths


@pytest.mark.asyncio
async def test_blackbox_spatial_and_damage_heatmap(
    client: TestClient,
    worker: CampaignAnalyticsWorker,
    event_bus: RedisStreamsEventBus,
) -> None:
    """Verify token movement and damage telemetry projections into heatmap densities."""
    campaign_id, session_id, char_id = uuid4(), uuid4(), uuid4()
    token_id = str(char_id)
    await worker.setup_groups()

    # 1. Publish SessionCreated
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionCreated(
            aggregate_id=session_id,
            campaign_id=campaign_id,
            session_id=session_id,
            title="Assault on Castle Ravenloft",
        ),
    )
    # 2. Place token and move it across tactical grid
    await event_bus.publish_event(
        "runefoble.events.board",
        TokenPlaced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            token_id=token_id,
            name="Valeros Fighter",
            token_type="pc",
            x=10,
            y=15,
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.board",
        TokenMoved(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            token_id=token_id,
            name="Valeros Fighter",
            from_x=10,
            from_y=15,
            to_x=12,
            to_y=18,
        ),
    )
    # 3. Apply character damage at new coordinate
    await event_bus.publish_event(
        "runefoble.events.character",
        CharacterHealthChanged(
            aggregate_id=char_id,
            session_id=session_id,
            campaign_id=campaign_id,
            delta=-25,
            current_hp=15,
            max_hp=40,
            source="fireball",
        ),
    )

    # 4. Consume and project within sub-200ms latency budget
    t0 = time.perf_counter()
    processed = await worker.process_once(count=10)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert processed >= 4
    assert elapsed_ms < 200.0, f"Worker projection took {elapsed_ms}ms, exceeding 200ms SLA"

    # 5. Query heatmap REST frontdoor
    resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/heatmap?cell_size=5")
    assert resp.status_code == 200, resp.text
    heatmap = resp.json()
    assert heatmap["campaign_id"] == str(campaign_id)
    assert heatmap["total_points"] >= 3
    assert len(heatmap["cells"]) > 0

    # Bucket check: coordinate (12, 18) buckets to (10, 15) when cell_size=5
    target_cell = next((c for c in heatmap["cells"] if c["x"] == 10 and c["y"] == 15), None)
    assert target_cell is not None
    assert target_cell["movement_count"] >= 1
    assert target_cell["damage_total"] == 25
    assert target_cell["hit_count"] >= 1

    # 6. Granularity check: cell_size=10
    resp10 = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/heatmap?cell_size=10")
    assert resp10.status_code == 200
    h10 = resp10.json()
    assert h10["cell_size"] == 10
    assert any(c["x"] == 10 and c["y"] == 10 for c in h10["cells"])


@pytest.mark.asyncio
async def test_blackbox_combat_mvp_turn_statistics(
    client: TestClient,
    worker: CampaignAnalyticsWorker,
    event_bus: RedisStreamsEventBus,
) -> None:
    """Verify calculation of per-encounter MVP awards and combatant efficacy."""
    campaign_id, session_id = uuid4(), uuid4()
    valeros_id, kyra_id, dragon_id = uuid4(), uuid4(), uuid4()
    await worker.setup_groups()

    # Map session and start combat
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionCreated(
            aggregate_id=session_id,
            campaign_id=campaign_id,
            session_id=session_id,
            title="Red Dragon Lair",
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
    # Valeros rolls critical strike and attacks dragon
    await event_bus.publish_event(
        "runefoble.events.watcher",
        DiceRolled(
            aggregate_id=uuid4(),
            session_id=str(session_id),
            roller_id=str(valeros_id),
            roller_name="Valeros",
            formula="1d20+7",
            total=27,
            is_crit=True,
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        CombatRoundAdvanced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            round_number=1,
            active_combatant_id=str(valeros_id),
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.character",
        CharacterHealthChanged(
            aggregate_id=dragon_id,
            session_id=session_id,
            campaign_id=campaign_id,
            delta=-65,
            current_hp=135,
            max_hp=200,
            source="slashing",
        ),
    )
    await worker.process_once(count=10)

    # Kyra rolls dice and provides clutch healing in round 2
    await event_bus.publish_event(
        "runefoble.events.watcher",
        DiceRolled(
            aggregate_id=uuid4(),
            session_id=str(session_id),
            roller_id=str(kyra_id),
            roller_name="Kyra the Cleric",
            formula="2d8+4",
            total=16,
            is_crit=False,
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        CombatRoundAdvanced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            round_number=2,
            active_combatant_id=str(kyra_id),
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.character",
        CharacterHealthChanged(
            aggregate_id=valeros_id,
            session_id=session_id,
            campaign_id=campaign_id,
            delta=35,
            current_hp=40,
            max_hp=40,
            source="healing",
        ),
    )
    await worker.process_once(count=10)

    # Query MVP REST frontdoor
    resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/mvp")
    assert resp.status_code == 200, resp.text
    mvp_data = resp.json()
    assert mvp_data["campaign_id"] == str(campaign_id)
    assert mvp_data["overall_mvp"] is not None
    assert mvp_data["overall_mvp"]["recipient_id"] == str(valeros_id)

    awards = {a["title"]: a for a in mvp_data["awards"]}
    assert awards["Most Lethal"]["recipient_name"] == "Valeros"
    assert awards["Most Lethal"]["score"] == 65
    assert awards["Guardian Angel"]["recipient_name"] == "Kyra the Cleric"
    assert awards["Guardian Angel"]["score"] == 35
    assert awards["Nat 20 Master"]["recipient_name"] == "Valeros"


@pytest.mark.asyncio
async def test_blackbox_chronicle_milestone_timeline(
    client: TestClient,
    worker: CampaignAnalyticsWorker,
    event_bus: RedisStreamsEventBus,
) -> None:
    """Verify chronological timeline of session milestones, knockouts, and recaps."""
    campaign_id, session_id = uuid4(), uuid4()
    ezren_id, merisiel_id = uuid4(), uuid4()
    await worker.setup_groups()

    # 1. Session start
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionCreated(
            aggregate_id=session_id,
            campaign_id=campaign_id,
            session_id=session_id,
            title="The Sunless Citadel",
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionStarted(aggregate_id=session_id, session_id=session_id, campaign_id=campaign_id),
    )
    # 2. Token placed and knocked out at 0 HP
    await event_bus.publish_event(
        "runefoble.events.board",
        TokenPlaced(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            token_id=str(ezren_id),
            name="Ezren the Wizard",
            token_type="pc",
            x=20,
            y=25,
        ),
    )
    await event_bus.publish_event(
        "runefoble.events.character",
        CharacterHealthChanged(
            aggregate_id=ezren_id,
            session_id=session_id,
            campaign_id=campaign_id,
            delta=-30,
            current_hp=0,
            max_hp=24,
            source="dragon_breath",
        ),
    )
    # 3. Absentee recap
    await event_bus.publish_event(
        "runefoble.events.watcher",
        AbsenteeRecapGenerated(
            aggregate_id=uuid4(),
            session_id=str(session_id),
            character_id=str(merisiel_id),
            character_name="Merisiel Rogue",
            stand_in_persona="Sneaky Drunkard",
            narrative_summary="Merisiel stealthily flanked the hobgoblin sentries despite being drunk.",
            highlights=["Stole goblin key", "Disarmed spike trap"],
        ),
    )
    # 4. Session concluded
    await event_bus.publish_event(
        "runefoble.events.session",
        SessionEnded(
            aggregate_id=session_id,
            session_id=session_id,
            campaign_id=campaign_id,
            summary="Party defeated Belak the Outcast and retrieved the Gulthias fruit.",
        ),
    )
    await worker.process_once(count=10)

    # Query timeline REST frontdoor
    resp = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/timeline")
    assert resp.status_code == 200, resp.text
    t_data = resp.json()
    assert t_data["campaign_id"] == str(campaign_id)
    assert t_data["total_milestones"] >= 4

    types = [m["type"] for m in t_data["milestones"]]
    assert "session_start" in types
    assert "character_knockout" in types
    assert "recap" in types
    assert "session_end" in types

    ko = next(m for m in t_data["milestones"] if m["type"] == "character_knockout")
    assert "Ezren the Wizard" in ko["title"]
    assert "20, 25" in ko["description"]


@pytest.mark.asyncio
async def test_blackbox_spicedb_zanzibar_authorization(
    client: TestClient,
    storage: CampaignAnalyticsStorage,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify fine-grained SpiceDB Zanzibar permissions on campaign analytics endpoints."""
    campaign_id = "camp-secure-123"
    storage.session_to_campaign["sess-1"] = campaign_id

    # 1. Without credentials -> public view is permitted
    resp_pub = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/timeline")
    assert resp_pub.status_code == 200

    # 2. With unauthorized user ID header -> 403 Forbidden
    resp_forbidden = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/timeline",
        headers={"X-User-ID": "unauthorized-intruder"},
    )
    assert resp_forbidden.status_code == 403
    assert "Forbidden" in resp_forbidden.json()["detail"]

    # 3. Grant 'view' permission in Zanzibar -> 200 OK
    await spicedb_client.write_relationship(
        resource_type="campaign",
        resource_id=campaign_id,
        relation="view",
        subject_type="user",
        subject_id="authorized-player",
    )
    resp_ok = client.get(
        f"/api/v1/analytics/campaigns/{campaign_id}/timeline",
        headers={"X-User-ID": "authorized-player"},
    )
    assert resp_ok.status_code == 200
