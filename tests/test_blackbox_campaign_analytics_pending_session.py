"""Blackbox tests: rows recorded before a session maps to its campaign join that campaign.

Governed by ADR-0011 and Hard Invariant 7. Events enter through the Redis Streams transport.
Rows are read through the public heatmap, MVP, and timeline routes, and the public metrics route.
Until the session mapping arrives, rows wait with no campaign. They never carry the session id in
the campaign column.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from runefoble_events.board_events.token import TokenMoved
from runefoble_events.events import CharacterHealthChanged, SessionCreated

from tests.helpers.campaign_analytics_service import (
    BOARD_STREAM,
    CHARACTER_STREAM,
    SESSION_STREAM,
    AnalyticsService,
)
from tests.helpers.polling import wait_until


def _metric(client: Any, name: str) -> int:
    body: dict[str, Any] = client.get("/metrics").json()
    return int(body[name])


def _heatmap_points(client: Any, cid: str) -> int:
    body: dict[str, Any] = client.get(f"/api/v1/analytics/campaigns/{cid}/heatmap").json()
    return int(body["total_points"])


def _milestone_count(client: Any, cid: str) -> int:
    body: dict[str, Any] = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline").json()
    return int(body["total_milestones"])


def _combatant_field(client: Any, cid: str, combatant: str, field: str) -> int:
    body: dict[str, Any] = client.get(f"/api/v1/analytics/campaigns/{cid}/mvp").json()
    for row in body.get("combatants", []):
        if row["combatant_id"] == combatant:
            return int(row[field])
    return 0


def _token_moved(sid: str, tok: str) -> TokenMoved:
    return TokenMoved(
        aggregate_id=sid,
        session_id=sid,
        token_id=tok,
        name="Valeros",
        from_x=0,
        from_y=0,
        to_x=2,
        to_y=3,
    )


def _damage_to_zero(sid: str, kyra: str) -> CharacterHealthChanged:
    return CharacterHealthChanged(
        aggregate_id=kyra,
        session_id=sid,
        delta=-65,
        current_hp=0,
        max_hp=80,
    )


def test_rows_recorded_before_session_mapping_join_campaign_on_creation(
    analytics_service: AnalyticsService,
) -> None:
    """Movement, damage, and a knockout published before SessionCreated appear under the campaign."""
    cid, sid, tok, kyra = str(uuid4()), str(uuid4()), str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        spatial_before = _metric(client, "spatial_records_count")
        milestones_before = _metric(client, "milestones_count")
        analytics_service.publish(BOARD_STREAM, _token_moved(sid, tok))
        analytics_service.publish(CHARACTER_STREAM, _damage_to_zero(sid, kyra))
        # Pending rows are invisible to campaign queries. The shared counters show they are stored.
        assert wait_until(
            lambda: (
                _metric(client, "spatial_records_count") == spatial_before + 3
                and _metric(client, "milestones_count") == milestones_before + 1
            ),
            timeout_s=10.0,
        )
        assert _heatmap_points(client, cid) == 0

        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="Vault"),
        )
        assert wait_until(lambda: _milestone_count(client, cid) == 2, timeout_s=10.0)
        assert wait_until(lambda: _heatmap_points(client, cid) == 3, timeout_s=10.0)
        assert _combatant_field(client, cid, kyra, "damage_taken") == 65


def test_session_id_is_not_a_campaign_id_for_pending_rows(
    analytics_service: AnalyticsService,
) -> None:
    """A session id names no campaign. Rows recorded under that session never answer to it."""
    cid, sid, tok, kyra = str(uuid4()), str(uuid4()), str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)
    analytics_service.grant_view(sid)

    with analytics_service.start() as client:
        spatial_before = _metric(client, "spatial_records_count")
        analytics_service.publish(BOARD_STREAM, _token_moved(sid, tok))
        analytics_service.publish(CHARACTER_STREAM, _damage_to_zero(sid, kyra))
        assert wait_until(
            lambda: _metric(client, "spatial_records_count") == spatial_before + 3,
            timeout_s=10.0,
        )
        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="Vault"),
        )
        assert wait_until(lambda: _heatmap_points(client, cid) == 3, timeout_s=10.0)
        assert _heatmap_points(client, sid) == 0


def test_redelivered_pending_rows_are_not_projected_twice(
    analytics_service: AnalyticsService,
) -> None:
    """Redelivering pending messages after the mapping adds no second row or milestone."""
    cid, sid, tok, kyra = str(uuid4()), str(uuid4()), str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        spatial_before = _metric(client, "spatial_records_count")
        milestones_before = _metric(client, "milestones_count")
        analytics_service.publish(BOARD_STREAM, _token_moved(sid, tok))
        analytics_service.publish(CHARACTER_STREAM, _damage_to_zero(sid, kyra))
        assert wait_until(
            lambda: (
                _metric(client, "spatial_records_count") == spatial_before + 3
                and _metric(client, "milestones_count") == milestones_before + 1
            ),
            timeout_s=10.0,
        )
        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="Vault"),
        )
        assert wait_until(lambda: _milestone_count(client, cid) == 2, timeout_s=10.0)

        analytics_service.redeliver(BOARD_STREAM)
        analytics_service.redeliver(CHARACTER_STREAM)
        # The session stream is ordered after the redelivery. Its sentinel shows the replay ended.
        analytics_service.publish(
            SESSION_STREAM,
            SessionCreated(aggregate_id=sid, session_id=sid, campaign_id=cid, title="Sentinel"),
        )
        assert wait_until(lambda: _milestone_count(client, cid) == 3, timeout_s=10.0)
        assert _heatmap_points(client, cid) == 3
        assert _metric(client, "spatial_records_count") == spatial_before + 3
        assert _metric(client, "milestones_count") == milestones_before + 3
