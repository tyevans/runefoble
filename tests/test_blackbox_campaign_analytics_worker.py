"""Blackbox tests for the Campaign Analytics stream projection.

Governed by ADR-0006 (Redis Streams), ADR-0011, Hard Invariant 2, and Hard Invariant 7.
Events enter through the Redis Streams transport. Projections are read through public routes.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from runefoble_events.events import (
    AbsenteeRecapGenerated,
    CharacterHealthChanged,
    SessionCreated,
    SessionEnded,
    SessionStarted,
    TokenMoved,
    TokenPlaced,
)

from tests.helpers.campaign_analytics_service import (
    BOARD_STREAM,
    CHARACTER_STREAM,
    SESSION_STREAM,
    WATCHER_STREAM,
    AnalyticsService,
)
from tests.helpers.polling import wait_until


def _milestone_types(client: Any, cid: str) -> list[str]:
    body = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline?limit=500").json()
    return [m["type"] for m in body.get("milestones", [])]


def _heatmap_points(client: Any, cid: str, metric: str = "all") -> int:
    body = client.get(f"/api/v1/analytics/campaigns/{cid}/heatmap?metric={metric}").json()
    return int(body["total_points"])


def test_session_lifecycle_and_recap_become_chronicle_milestones(
    analytics_service: AnalyticsService,
) -> None:
    """Session start, recap, and end each appear on the campaign timeline.

    Each stream has its own consumer, so the order across streams is not asserted.
    """
    cid, sid, char = str(uuid4()), str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="Vault"),
        )
        analytics_service.publish(
            SESSION_STREAM, SessionStarted(aggregate_id=sid, session_id=sid, campaign_id=cid)
        )
        analytics_service.publish(
            WATCHER_STREAM,
            AbsenteeRecapGenerated(
                aggregate_id=uuid4(),
                session_id=str(sid),
                character_id=char,
                character_name="Merisiel Rogue",
                stand_in_persona="Sneaky Drunkard",
                narrative_summary="Merisiel flanked the sentries.",
                highlights=["Stole key"],
            ),
        )
        analytics_service.publish(
            SESSION_STREAM,
            SessionEnded(aggregate_id=sid, session_id=sid, campaign_id=cid, summary="Finished"),
        )

        assert wait_until(lambda: "session_end" in _milestone_types(client, cid), timeout_s=10.0)
        assert sorted(_milestone_types(client, cid)) == sorted(
            ["session_start", "session_start", "recap", "session_end"]
        )


def test_placement_movement_and_knockout_are_projected(analytics_service: AnalyticsService) -> None:
    """Token placement and movement are heatmap points. A knockout adds a chronicle milestone."""
    cid, sid, tok = str(uuid4()), str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        analytics_service.publish(
            BOARD_STREAM,
            TokenPlaced(
                aggregate_id=sid,
                session_id=sid,
                campaign_id=cid,
                token_id=tok,
                name="Kyra",
                token_type="pc",
                x=5,
                y=5,
            ),
        )
        assert wait_until(lambda: _heatmap_points(client, cid) == 1, timeout_s=10.0)
        analytics_service.publish(
            BOARD_STREAM,
            TokenMoved(
                aggregate_id=sid,
                session_id=sid,
                campaign_id=cid,
                token_id=tok,
                name="Kyra",
                from_x=5,
                from_y=5,
                to_x=7,
                to_y=8,
            ),
        )
        assert wait_until(lambda: _heatmap_points(client, cid, "movement") == 2, timeout_s=10.0)

        analytics_service.publish(
            CHARACTER_STREAM,
            CharacterHealthChanged(
                aggregate_id=tok,
                session_id=sid,
                campaign_id=cid,
                delta=-15,
                current_hp=0,
                max_hp=30,
            ),
        )
        assert wait_until(
            lambda: "character_knockout" in _milestone_types(client, cid), timeout_s=10.0
        )
        timeline = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline").json()
        knockout = next(m for m in timeline["milestones"] if m["type"] == "character_knockout")
        assert knockout["title"] == "Kyra Knocked Unconscious"
        assert knockout["metadata"]["coordinates"] == [7, 8]
