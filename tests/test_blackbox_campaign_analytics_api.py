"""Blackbox frontdoor tests for Campaign Analytics REST routes and authorization.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- ADR-0015: bearer tokens and SpiceDB object authorization
- Hard Invariant 1: SpiceDB Zanzibar object authorization
- Hard Invariant 7: Blackbox TDD with Frontdoor Setup

Setup publishes domain events to the Redis Streams transport. Assertions read public routes.
"""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from runefoble_events.events import CharacterHealthChanged, CombatRoundAdvanced, SessionCreated

from tests.helpers.campaign_analytics_service import (
    CHARACTER_STREAM,
    SESSION_STREAM,
    AnalyticsService,
    bearer,
    wait_until,
)


def _timeline_titles(client: TestClient, cid: str) -> list[str]:
    body = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline").json()
    return [m["title"] for m in body.get("milestones", [])]


def test_service_healthz_metrics_and_manifest(analytics_service: AnalyticsService) -> None:
    """Verify /healthz, /metrics, /openapi.json, and /ui/manifest public frontdoors."""
    with analytics_service.start() as client:
        health = client.get("/healthz").json()
        assert health == {
            "status": "ok",
            "service": "campaign-analytics",
            "consumers": {"analytics": "running"},
        }
        metrics = client.get("/metrics").json()
        assert metrics["spatial_records_count"] == 0
        assert metrics["milestones_count"] == 0

        paths = client.get("/openapi.json").json()["paths"]
        assert "/api/v1/analytics/campaigns/{id}/heatmap" in paths
        assert "/api/v1/analytics/campaigns/{id}/mvp" in paths
        assert "/api/v1/analytics/campaigns/{id}/timeline" in paths

        manifest = client.get("/ui/manifest").json()
        assert manifest["service"] == "campaign-analytics"
        assert "runefoble-combat-heatmap" in manifest["components"]


def test_mvp_route_filters_by_encounter(analytics_service: AnalyticsService) -> None:
    """The MVP route returns only combatants of the requested encounter."""
    cid, sid = str(uuid4()), str(uuid4())
    valeros, kyra = str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="Boss"),
        )
        analytics_service.publish(
            SESSION_STREAM,
            CombatRoundAdvanced(
                aggregate_id=sid,
                session_id=sid,
                campaign_id=cid,
                round_number=1,
                active_combatant_id=valeros,
            ),
        )
        # Session and character streams are consumed by separate loops. Wait for the round,
        # so the damage is credited to the active combatant.
        assert wait_until(lambda: "Combat Round 1" in _timeline_titles(client, cid))
        analytics_service.publish(
            CHARACTER_STREAM,
            CharacterHealthChanged(
                aggregate_id=kyra,
                session_id=sid,
                campaign_id=cid,
                delta=-65,
                current_hp=10,
                max_hp=80,
            ),
        )

        def valeros_dealt_damage() -> bool:
            body = client.get(f"/api/v1/analytics/campaigns/{cid}/mvp").json()
            return any(
                c["combatant_id"] == valeros and c["damage_dealt"] == 65
                for c in body.get("combatants", [])
            )

        assert wait_until(valeros_dealt_damage)

        resp = client.get(
            f"/api/v1/analytics/campaigns/{cid}/mvp?session_id={sid}&encounter_id=enc-none"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["combatants"] == []
        assert resp.json()["overall_mvp"] is None


def test_timeline_route_applies_limit(analytics_service: AnalyticsService) -> None:
    """The timeline route returns the total count and only `limit` milestones."""
    cid, sid = str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="One"),
        )
        analytics_service.publish(
            SESSION_STREAM,
            CombatRoundAdvanced(
                aggregate_id=sid,
                session_id=sid,
                campaign_id=cid,
                round_number=2,
                active_combatant_id="",
            ),
        )
        assert wait_until(lambda: len(_timeline_titles(client, cid)) == 2)

        resp = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline?limit=1")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total_milestones"] == 2
        assert len(body["milestones"]) == 1


def test_campaign_analytics_routes_require_view_permission(
    analytics_service: AnalyticsService,
) -> None:
    """Anonymous callers get 401. Callers without view rights get 403. Viewers get 200."""
    cid = str(uuid4())
    with analytics_service.start(authenticated=False) as anon:
        assert anon.get(f"/api/v1/analytics/campaigns/{cid}/timeline").status_code == 401

    intruder_headers = bearer("unauthorized-intruder")
    viewer_headers = bearer("authorized-player")
    analytics_service.grant_view(cid, user_id="authorized-player")

    with analytics_service.start() as client:
        for endpoint in ("timeline", "heatmap", "mvp"):
            resp = client.get(
                f"/api/v1/analytics/campaigns/{cid}/{endpoint}", headers=intruder_headers
            )
            assert resp.status_code == 403
            assert "Forbidden" in resp.json()["detail"]

        resp_ok = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline", headers=viewer_headers)
        assert resp_ok.status_code == 200
