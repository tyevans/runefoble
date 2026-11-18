"""Blackbox TDD test suite for TypeScript Audience Studio Microservice (TASK-0051).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Interacts strictly through public Fastify REST routes, WebSockets,
and published CloudEvents over Redis Streams.
"""

from __future__ import annotations

from collections.abc import Generator

import httpx
import pytest
from runefoble_events.events import (
    AudiencePollStarted,
)

from tests.helpers.audience_server import AudienceStudioProcess, start_audience_studio_server


@pytest.fixture(scope="module")
def audience() -> Generator[AudienceStudioProcess]:
    """Launch Audience Studio Fastify server as an isolated subprocess."""
    yield from start_audience_studio_server()


def _auth(audience: AudienceStudioProcess, sub: str) -> dict[str, str]:
    """Bearer header for a verified Zitadel-style token. The service rejects every other caller."""
    return {"Authorization": f"Bearer {audience.token(sub)}"}


def test_healthz_readyz_and_ui_manifest(audience: AudienceStudioProcess):
    """Verify health probes and ADR-0013 microfrontend discovery manifest."""
    with httpx.Client(base_url=audience.base_url) as client:
        res_h = client.get("/healthz")
        assert res_h.status_code == 200
        assert res_h.json() == {"status": "ok", "service": "audience_studio"}

        res_r = client.get("/readyz")
        assert res_r.status_code == 200
        assert res_r.json() == {"status": "ready", "service": "audience_studio"}

        res_m = client.get("/ui/manifest")
        assert res_m.status_code == 200
        man = res_m.json()
        assert man["service"] == "audience_studio"
        assert man["package"] == "@runefoble/audience-studio-ui"
        assert "runefoble-audience-studio" in man["components"]


def test_openapi_spec_exposure(audience: AudienceStudioProcess):
    """Verify OpenAPI 3.0 specification is exposed for Swagger UI hub aggregation."""
    with httpx.Client(base_url=audience.base_url) as client:
        res = client.get("/openapi.json", headers=_auth(audience, "spec-reader"))
        assert res.status_code == 200
        schema = res.json()
        assert schema["openapi"].startswith("3.")
        assert schema["info"]["title"] == "Runefoble Audience Studio API"
        paths = schema["paths"]
        assert "/api/v1/audience/polls" in paths
        assert "/api/v1/audience/proposals" in paths


def test_protected_routes_refuse_callers_without_a_verified_token(audience: AudienceStudioProcess):
    """Verify no bearer token, and the removed tuple route, never reach a handler."""
    with httpx.Client(base_url=audience.base_url) as client:
        unauthenticated = client.post(
            "/api/v1/audience/polls",
            json={"campaign_id": "camp-anon", "title": "T", "prompt": "P", "options": ["A"]},
        )
        assert unauthenticated.status_code == 401

        tuple_route = client.post(
            "/api/v1/audience/auth/tuples",
            headers=_auth(audience, "mallory"),
            json={
                "resource_type": "campaign",
                "resource_id": "camp-omega",
                "relation": "dungeon_master",
                "subject_type": "user",
                "subject_id": "mallory",
            },
        )
        assert tuple_route.status_code == 404


def test_poll_lifecycle_spectator_voting_and_quorum(audience: AudienceStudioProcess):
    """Verify poll creation, vote casting, deduplication, and quorum aggregation."""
    with httpx.Client(base_url=audience.base_url) as client:
        # 1. Create a live chaos poll with quorum = 3
        res = client.post(
            "/api/v1/audience/polls",
            headers=_auth(audience, "dm-omega"),
            json={
                "campaign_id": "camp-omega",
                "title": "Chaos Surge Element",
                "prompt": "Choose which elemental hazard spawns on the grid!",
                "options": ["Fire Storm", "Acid Pool", "Frozen Mist"],
                "duration_seconds": 60,
                "quorum": 3,
            },
        )
        assert res.status_code == 201
        poll = res.json()
        poll_id = poll["id"]
        assert poll["status"] == "active"
        assert poll["totalVotes"] == 0
        assert len(poll["options"]) == 3

        # 2. Spectator voting via REST frontdoor
        res_v1 = client.post(
            f"/api/v1/audience/polls/{poll_id}/votes",
            headers=_auth(audience, "user-twitch-1"),
            json={"option_id": "opt_1", "channel": "twitch"},
        )
        assert res_v1.status_code == 200
        assert res_v1.json()["poll"]["totalVotes"] == 1

        res_v2 = client.post(
            f"/api/v1/audience/polls/{poll_id}/votes",
            headers=_auth(audience, "user-youtube-2"),
            json={"option_id": "opt_1", "channel": "youtube"},
        )
        assert res_v2.status_code == 200

        res_v3 = client.post(
            f"/api/v1/audience/polls/{poll_id}/votes",
            headers=_auth(audience, "user-web-3"),
            json={"option_id": "opt_2", "channel": "web"},
        )
        assert res_v3.status_code == 200

        # Duplicate vote by user-twitch-1 rejected
        res_dup = client.post(
            f"/api/v1/audience/polls/{poll_id}/votes",
            headers=_auth(audience, "user-twitch-1"),
            json={"option_id": "opt_3"},
        )
        assert res_dup.status_code == 400
        assert "already voted" in res_dup.json()["error"]

        # 3. Close poll and verify quorum aggregation
        res_close = client.post(
            f"/api/v1/audience/polls/{poll_id}/close",
            headers=_auth(audience, "dm-omega"),
        )
        assert res_close.status_code == 200
        closed = res_close.json()
        assert closed["status"] == "completed"
        assert closed["totalVotes"] == 3
        assert closed["quorumMet"] is True
        assert closed["winningOptionId"] == "opt_1"
        assert closed["proposedModifier"] is not None
        assert closed["proposedModifier"]["status"] == "pending"


def test_quorum_not_met_scenario(audience: AudienceStudioProcess):
    """Verify poll where quorum is not reached yields completed status without modifier."""
    with httpx.Client(base_url=audience.base_url) as client:
        res = client.post(
            "/api/v1/audience/polls",
            headers=_auth(audience, "dm-quorum"),
            json={
                "campaign_id": "camp-quorum-fail",
                "title": "High Quorum Poll",
                "prompt": "Requires 50 votes",
                "options": ["A", "B"],
                "quorum": 50,
            },
        )
        poll_id = res.json()["id"]

        client.post(
            f"/api/v1/audience/polls/{poll_id}/votes",
            headers=_auth(audience, "solo-voter"),
            json={"option_id": "opt_1"},
        )

        closed = client.post(
            f"/api/v1/audience/polls/{poll_id}/close",
            headers=_auth(audience, "dm-quorum"),
        ).json()
        assert closed["status"] == "completed"
        assert closed["totalVotes"] == 1
        assert closed["quorumMet"] is False
        assert closed.get("proposedModifier") is None


def test_cloudevents_specification_compliance():
    """Verify Python domain events adhere strictly to CloudEvents 1.0 JSON format."""
    event = AudiencePollStarted(
        poll_id="poll-test",
        campaign_id="camp-test",
        title="CE Test",
        prompt="Prompt",
        options=[{"id": "o1", "label": "A", "votes": 0}],
    )
    ce = event.to_cloudevent_dict()
    assert ce["specversion"] == "1.0"
    assert ce["type"] == "runefoble.events.audience.poll_started"
    assert ce["datacontenttype"] == "application/json"
    assert "data" in ce
    assert ce["data"]["poll_id"] == "poll-test"
