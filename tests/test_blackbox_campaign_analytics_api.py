"""Blackbox TDD frontdoor test suite for Campaign Analytics REST API endpoints.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0005: Kubernetes-First Infrastructure with Helm and Kind
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 6: File length limit (< 500 lines, target < 200 lines)
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from campaign_analytics.dependencies import set_spicedb_client, set_storage, set_worker
from campaign_analytics.main import app
from campaign_analytics.storage import CampaignAnalyticsStorage
from campaign_analytics.worker import CampaignAnalyticsWorker
from fastapi.testclient import TestClient
from runefoble_auth.mock_spicedb import MockSpiceDBClient
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup


@pytest.fixture
def storage() -> CampaignAnalyticsStorage:
    return CampaignAnalyticsStorage()


@pytest.fixture
def spicedb_client() -> MockSpiceDBClient:
    return MockSpiceDBClient()


@pytest.fixture
def client(storage: CampaignAnalyticsStorage, spicedb_client: MockSpiceDBClient) -> TestClient:
    mock_redis = MockAsyncRedis()
    cg = RedisConsumerGroup(client=mock_redis)
    worker = CampaignAnalyticsWorker(storage=storage, consumer_group=cg)
    set_storage(storage)
    set_worker(worker)
    set_spicedb_client(spicedb_client)
    return TestClient(app)


def test_service_healthz_metrics_and_manifest(client: TestClient) -> None:
    """Verify /healthz, /metrics, /openapi.json, and /ui/manifest public frontdoors."""
    assert client.get("/healthz").json() == {"status": "ok", "service": "campaign-analytics"}
    assert "spatial_records_count" in client.get("/metrics").json()
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/analytics/campaigns/{id}/heatmap" in paths
    assert "/api/v1/analytics/campaigns/{id}/mvp" in paths
    assert "/api/v1/analytics/campaigns/{id}/timeline" in paths

    manifest = client.get("/ui/manifest").json()
    assert manifest["service"] == "campaign-analytics"
    assert "runefoble-combat-heatmap" in manifest["components"]


@pytest.mark.asyncio
async def test_campaign_analytics_api_heatmap(
    client: TestClient, storage: CampaignAnalyticsStorage
) -> None:
    """Verify spatial heatmap REST endpoint schemas, bucketing, and query parameters."""
    cid, sid = str(uuid4()), str(uuid4())
    await storage.record_spatial(cid, sid, "tok-1", "Valeros", 12, 18, "movement")
    await storage.record_spatial(cid, sid, "tok-1", "Valeros", 12, 18, "damage", damage=25)

    # Default cell_size=5
    resp = client.get(f"/api/v1/analytics/campaigns/{cid}/heatmap?session_id={sid}")
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["campaign_id"] == cid
    assert data["session_id"] == sid
    assert data["total_points"] == 2
    cell = next(c for c in data["cells"] if c["x"] == 10 and c["y"] == 15)
    assert cell["movement_count"] == 1
    assert cell["damage_total"] == 25

    # Filter cell_size=10 and metric=damage
    resp10 = client.get(
        f"/api/v1/analytics/campaigns/{cid}/heatmap?cell_size=10&metric=damage&session_id={sid}"
    )
    assert resp10.status_code == 200
    d10 = resp10.json()
    assert d10["cell_size"] == 10
    assert d10["total_points"] == 1


@pytest.mark.asyncio
async def test_campaign_analytics_api_mvp(
    client: TestClient, storage: CampaignAnalyticsStorage
) -> None:
    """Verify combat MVP statistics REST endpoint and encounter filtering."""
    cid, sid, enc_id = str(uuid4()), str(uuid4()), "enc-boss"
    valeros_id, kyra_id = str(uuid4()), str(uuid4())

    await storage.record_combatant_stat(
        cid, sid, enc_id, valeros_id, "Valeros", damage_dealt=65, critical_hits=1, turns_taken=1
    )
    await storage.record_combatant_stat(
        cid, sid, enc_id, kyra_id, "Kyra", healing_provided=35, turns_taken=1
    )

    resp = client.get(
        f"/api/v1/analytics/campaigns/{cid}/mvp?session_id={sid}&encounter_id={enc_id}"
    )
    assert resp.status_code == 200, resp.text
    mvp_data = resp.json()
    assert mvp_data["campaign_id"] == cid
    assert mvp_data["overall_mvp"]["recipient_id"] == valeros_id

    awards = {a["title"]: a for a in mvp_data["awards"]}
    assert awards["Most Lethal"]["recipient_name"] == "Valeros"
    assert awards["Most Lethal"]["score"] == 65
    assert awards["Guardian Angel"]["recipient_name"] == "Kyra"
    assert awards["Guardian Angel"]["score"] == 35


@pytest.mark.asyncio
async def test_campaign_analytics_api_timeline(
    client: TestClient, storage: CampaignAnalyticsStorage
) -> None:
    """Verify chronicle milestone timeline REST endpoint and limit parameter filtering."""
    cid, sid = str(uuid4()), str(uuid4())
    await storage.record_milestone(
        cid, sid, "session_start", "Session Started", "Began", "2026-09-01"
    )
    await storage.record_milestone(cid, sid, "recap", "Chronicle Recap", "Summary", "2026-09-02")
    await storage.record_milestone(cid, sid, "session_end", "Session Ended", "Ended", "2026-09-03")

    resp = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline?limit=2")
    assert resp.status_code == 200, resp.text
    t_data = resp.json()
    assert t_data["campaign_id"] == cid
    assert t_data["total_milestones"] == 3
    assert len(t_data["milestones"]) == 2
    assert t_data["milestones"][0]["type"] == "session_start"


@pytest.mark.asyncio
async def test_blackbox_spicedb_zanzibar_authorization(
    client: TestClient,
    storage: CampaignAnalyticsStorage,
    spicedb_client: MockSpiceDBClient,
) -> None:
    """Verify fine-grained SpiceDB Zanzibar permissions across campaign analytics endpoints."""
    campaign_id = "camp-secure-123"
    storage.session_to_campaign["sess-1"] = campaign_id

    # 1. Without credentials -> public view is permitted
    resp_pub = client.get(f"/api/v1/analytics/campaigns/{campaign_id}/timeline")
    assert resp_pub.status_code == 200

    # 2. With unauthorized user ID header -> 403 Forbidden across all routers
    for endpoint in ("timeline", "heatmap", "mvp"):
        resp_forbidden = client.get(
            f"/api/v1/analytics/campaigns/{campaign_id}/{endpoint}",
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
