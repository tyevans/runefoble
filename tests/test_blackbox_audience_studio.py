"""Blackbox TDD test suite for TypeScript Audience Studio Microservice (TASK-0051).

Governed by Hard Invariant 7 (Blackbox TDD with Frontdoor Setup).
Interacts strictly through public Fastify REST routes, WebSockets,
and published CloudEvents over Redis Streams.
"""

from __future__ import annotations

from collections.abc import Generator

import httpx
import pytest
from runefoble_events import (
    AudiencePollStarted,
)

from tests.helpers.audience_server import start_audience_studio_server


@pytest.fixture(scope="module")
def audience_url() -> Generator[str]:
    """Launch Audience Studio Fastify server as an isolated subprocess."""
    yield from start_audience_studio_server()


def test_healthz_readyz_and_ui_manifest(audience_url: str):
    """Verify health probes and ADR-0013 microfrontend discovery manifest."""
    with httpx.Client(base_url=audience_url) as client:
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


def test_openapi_spec_exposure(audience_url: str):
    """Verify OpenAPI 3.0 specification is exposed for Swagger UI hub aggregation."""
    with httpx.Client(base_url=audience_url) as client:
        res = client.get("/openapi.json")
        assert res.status_code == 200
        schema = res.json()
        assert schema["openapi"].startswith("3.")
        assert schema["info"]["title"] == "Runefoble Audience Studio API"
        paths = schema["paths"]
        assert "/api/v1/audience/polls" in paths
        assert "/api/v1/audience/proposals" in paths


def test_poll_lifecycle_spectator_voting_and_quorum(audience_url: str):
    """Verify poll creation, vote casting, deduplication, and quorum aggregation."""
    with httpx.Client(base_url=audience_url) as client:
        # 1. Create a live chaos poll with quorum = 3
        res = client.post(
            "/api/v1/audience/polls",
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
            json={"voter_id": "user-twitch-1", "option_id": "opt_1", "channel": "twitch"},
        )
        assert res_v1.status_code == 200
        assert res_v1.json()["poll"]["totalVotes"] == 1

        res_v2 = client.post(
            f"/api/v1/audience/polls/{poll_id}/votes",
            json={"voter_id": "user-youtube-2", "option_id": "opt_1", "channel": "youtube"},
        )
        assert res_v2.status_code == 200

        res_v3 = client.post(
            f"/api/v1/audience/polls/{poll_id}/votes",
            json={"voter_id": "user-web-3", "option_id": "opt_2", "channel": "web"},
        )
        assert res_v3.status_code == 200

        # Duplicate vote by user-twitch-1 rejected
        res_dup = client.post(
            f"/api/v1/audience/polls/{poll_id}/votes",
            json={"voter_id": "user-twitch-1", "option_id": "opt_3"},
        )
        assert res_dup.status_code == 400
        assert "already voted" in res_dup.json()["error"]

        # 3. Close poll and verify quorum aggregation
        res_close = client.post(f"/api/v1/audience/polls/{poll_id}/close")
        assert res_close.status_code == 200
        closed = res_close.json()
        assert closed["status"] == "completed"
        assert closed["totalVotes"] == 3
        assert closed["quorumMet"] is True
        assert closed["winningOptionId"] == "opt_1"
        assert closed["proposedModifier"] is not None
        assert closed["proposedModifier"]["status"] == "pending"


def test_quorum_not_met_scenario(audience_url: str):
    """Verify poll where quorum is not reached yields completed status without modifier."""
    with httpx.Client(base_url=audience_url) as client:
        res = client.post(
            "/api/v1/audience/polls",
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
            json={"voter_id": "solo-voter", "option_id": "opt_1"},
        )

        closed = client.post(f"/api/v1/audience/polls/{poll_id}/close").json()
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
