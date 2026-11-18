"""Blackbox frontdoor tests: gateway analytics views proxy to campaign_analytics (TASK-0588).

The gateway is called through its public HTTP routes. The owner is either a live
campaign_analytics app served on a loopback port, or a stand-in HTTP server for the
failure cases (ADR-0014, ADR-0015 b). Telemetry is published to the Redis Streams path
that the owner consumes. The gateway returns the owner's answer and never a substitute.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from gateway_api.main import app as gateway_app
from runefoble_events.events import CharacterHealthChanged, InitiativeTurnAdvanced, SessionCreated

from tests.helpers.campaign_analytics_service import (
    CHARACTER_STREAM,
    SESSION_STREAM,
    AnalyticsService,
    wait_until,
)
from tests.helpers.live_services import closed_port_url, serve

OWNER_FORBIDDEN_DETAIL = "Forbidden: User lacks permission to view campaign analytics"


def _auth(issuer, sub: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issuer.mint(sub)}"}


def _create_campaign(client: TestClient, issuer) -> str:
    """Create a campaign through the gateway. dm_valeros becomes its Zanzibar owner."""
    res = client.post(
        "/api/v1/campaigns",
        json={
            "title": "Tomb of the Star-Eater",
            "setting": "Astral Void",
            "system": "5e",
            "description": "Analytics views.",
        },
        headers=_auth(issuer, "dm_valeros"),
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def _recording_owner(seen: list[dict[str, Any]]) -> FastAPI:
    """Return a stand-in owner that records the query and bearer it receives."""
    app = FastAPI()

    @app.get("/{path:path}")
    def _echo(request: Request) -> dict[str, Any]:
        seen.append(
            {
                "path": request.url.path,
                "query": dict(request.query_params),
                "authorization": request.headers.get("authorization"),
            }
        )
        return {"campaign_id": "stand-in", "cells": [], "milestones": []}

    return app


def _forbidding_owner() -> FastAPI:
    """Return a stand-in owner that answers every route with the owner's 403 body."""
    app = FastAPI()

    @app.get("/{path:path}")
    def _forbidden(path: str) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": OWNER_FORBIDDEN_DETAIL})

    return app


@pytest.fixture
def live_owner(analytics_service: AnalyticsService, monkeypatch) -> Iterator[AnalyticsService]:
    """Serve campaign_analytics as a live loopback upstream, with its lifespan running."""
    from campaign_analytics.main import app as analytics_app

    with serve(analytics_app, lifespan="on") as url:
        monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_ANALYTICS_URL", url)
        yield analytics_service


@pytest.fixture
def live_client(live_owner, game_session_upstream) -> Iterator[TestClient]:
    """Run the gateway lifespan after the live owner URL is set."""
    with TestClient(gateway_app) as client:
        yield client


@pytest.fixture
def live_campaign(live_owner: AnalyticsService, live_client: TestClient, trusted_ws_issuer) -> str:
    """Create a campaign through the gateway, then grant its view relation on the shared double.

    game_session writes ownership tuples to its own SpiceDB seam. The live owner and the gateway
    read the analytics double, so the view relation is written there. Existing owner tests use
    the same `grant_view` pattern.
    """
    cid = _create_campaign(live_client, trusted_ws_issuer)
    live_owner.grant_view(cid, "dm_valeros")
    return cid


def _milestone_titles(client: TestClient, cid: str, headers: dict[str, str]) -> list[str]:
    body = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline", headers=headers).json()
    return [m["title"] for m in body.get("milestones", [])]


def test_heatmap_without_telemetry_returns_owner_empty_grid(
    live_client: TestClient, live_campaign: str, trusted_ws_issuer
) -> None:
    res = live_client.get(
        f"/api/v1/analytics/campaigns/{live_campaign}/heatmap",
        headers=_auth(trusted_ws_issuer, "dm_valeros"),
    )

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["campaign_id"] == live_campaign
    assert body["cells"] == []
    assert body["total_points"] == 0


def test_heatmap_forwards_cell_size_and_metric_to_owner(
    live_client: TestClient, live_campaign: str, trusted_ws_issuer
) -> None:
    res = live_client.get(
        f"/api/v1/analytics/campaigns/{live_campaign}/heatmap?cell_size=10&metric=damage",
        headers=_auth(trusted_ws_issuer, "dm_valeros"),
    )

    assert res.status_code == 200, res.text
    assert res.json()["cell_size"] == 10
    assert res.json()["metric"] == "damage"


def test_mvp_returns_owner_award_for_recorded_encounter(
    live_owner: AnalyticsService,
    live_client: TestClient,
    live_campaign: str,
    trusted_ws_issuer,
) -> None:
    sid, striker, victim = str(uuid4()), str(uuid4()), str(uuid4())
    headers = _auth(trusted_ws_issuer, "dm_valeros")
    live_owner.publish(
        SESSION_STREAM,
        SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=live_campaign, title="Crypt"),
    )
    live_owner.publish(
        SESSION_STREAM,
        InitiativeTurnAdvanced(
            aggregate_id=sid,
            session_id=sid,
            campaign_id=live_campaign,
            round_number=1,
            active_combatant_id=striker,
        ),
    )
    assert wait_until(
        lambda: "Combat Round 1" in _milestone_titles(live_client, live_campaign, headers)
    )
    live_owner.publish(
        CHARACTER_STREAM,
        CharacterHealthChanged(
            aggregate_id=victim,
            session_id=sid,
            campaign_id=live_campaign,
            delta=-65,
            current_hp=10,
            max_hp=80,
        ),
    )

    def striker_dealt_damage() -> bool:
        body = live_client.get(
            f"/api/v1/analytics/campaigns/{live_campaign}/mvp", headers=headers
        ).json()
        return any(
            c["combatant_id"] == striker and c["damage_dealt"] == 65
            for c in body.get("combatants", [])
        )

    assert wait_until(striker_dealt_damage)

    other = live_client.get(
        f"/api/v1/analytics/campaigns/{live_campaign}/mvp?encounter_id=enc-none", headers=headers
    )
    assert other.status_code == 200, other.text
    assert other.json()["combatants"] == []
    assert other.json()["overall_mvp"] is None


def test_timeline_forwards_limit_to_owner(
    live_owner: AnalyticsService,
    live_client: TestClient,
    live_campaign: str,
    trusted_ws_issuer,
) -> None:
    sid = str(uuid4())
    headers = _auth(trusted_ws_issuer, "dm_valeros")
    live_owner.publish(
        SESSION_STREAM,
        SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=live_campaign, title="One"),
    )
    live_owner.publish(
        SESSION_STREAM,
        InitiativeTurnAdvanced(
            aggregate_id=sid,
            session_id=sid,
            campaign_id=live_campaign,
            round_number=2,
            active_combatant_id="",
        ),
    )
    assert wait_until(lambda: len(_milestone_titles(live_client, live_campaign, headers)) == 2)

    res = live_client.get(
        f"/api/v1/analytics/campaigns/{live_campaign}/timeline?limit=1", headers=headers
    )

    assert res.status_code == 200, res.text
    assert res.json()["total_milestones"] == 2
    assert len(res.json()["milestones"]) == 1


def test_owner_forbidden_answer_passes_through(
    monkeypatch, game_session_upstream, trusted_ws_issuer
) -> None:
    with serve(_forbidding_owner()) as owner_url:
        monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_ANALYTICS_URL", owner_url)
        with TestClient(gateway_app) as client:
            cid = _create_campaign(client, trusted_ws_issuer)
            res = client.get(
                f"/api/v1/analytics/campaigns/{cid}/heatmap",
                headers=_auth(trusted_ws_issuer, "dm_valeros"),
            )

    assert res.status_code == 403
    assert res.json() == {"detail": OWNER_FORBIDDEN_DETAIL}


def test_owner_down_returns_503(monkeypatch, game_session_upstream, trusted_ws_issuer) -> None:
    monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_ANALYTICS_URL", closed_port_url())
    with TestClient(gateway_app) as client:
        cid = _create_campaign(client, trusted_ws_issuer)
        res = client.get(
            f"/api/v1/analytics/campaigns/{cid}/mvp",
            headers=_auth(trusted_ws_issuer, "dm_valeros"),
        )

    assert res.status_code == 503
    assert res.json()["upstream"] == "campaign_analytics"


def test_analytics_routes_forward_only_the_bearer_and_query(
    monkeypatch, game_session_upstream, trusted_ws_issuer
) -> None:
    seen: list[dict[str, Any]] = []
    with serve(_recording_owner(seen)) as owner_url:
        monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_ANALYTICS_URL", owner_url)
        with TestClient(gateway_app) as client:
            cid = _create_campaign(client, trusted_ws_issuer)
            headers = {**_auth(trusted_ws_issuer, "dm_valeros"), "X-User-Id": "spoofed"}
            cases = [
                (
                    f"/api/v1/analytics/campaigns/{cid}/heatmap"
                    "?session_id=s-1&cell_size=10&metric=damage",
                    {"session_id": "s-1", "cell_size": "10", "metric": "damage"},
                ),
                (
                    f"/api/v1/analytics/campaigns/{cid}/mvp?session_id=s-1&encounter_id=e-1",
                    {"session_id": "s-1", "encounter_id": "e-1"},
                ),
                (
                    f"/api/v1/analytics/campaigns/{cid}/timeline?session_id=s-1&limit=5",
                    {"session_id": "s-1", "limit": "5"},
                ),
            ]
            for url, expected_query in cases:
                res = client.get(url, headers=headers)
                assert res.status_code == 200, res.text
                assert seen[-1]["query"] == expected_query
                assert seen[-1]["authorization"] == headers["Authorization"]


def test_summary_route_is_not_served(monkeypatch, game_session_upstream, trusted_ws_issuer) -> None:
    with serve(_recording_owner([])) as owner_url:
        monkeypatch.setenv("RUNEFOBLE_CAMPAIGN_ANALYTICS_URL", owner_url)
        with TestClient(gateway_app) as client:
            cid = _create_campaign(client, trusted_ws_issuer)
            res = client.get(
                f"/api/v1/analytics/campaigns/{cid}", headers=_auth(trusted_ws_issuer, "dm_valeros")
            )

    assert res.status_code == 404
    assert "total_combat_turns" not in res.text
