"""Blackbox tests: a replayed stream message projects its chronicle milestone once.

Governed by ADR-0006 (Redis Streams), ADR-0011 (event sourcing), and Hard Invariant 7. Events
enter through the Redis Streams transport. Redelivery is a consumer group move to the start of
the stream, as Redis does on XGROUP SETID. Milestones are read through the public timeline route.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from runefoble_events.events import SessionEnded

from tests.helpers.campaign_analytics_service import (
    SESSION_STREAM,
    AnalyticsService,
)
from tests.helpers.polling import wait_until


def _session_end_descriptions(client: Any, cid: str) -> list[str]:
    body = client.get(f"/api/v1/analytics/campaigns/{cid}/timeline?limit=500").json()
    return sorted(m["description"] for m in body["milestones"] if m["type"] == "session_end")


def _session_ended(sid: str, cid: str, summary: str) -> SessionEnded:
    return SessionEnded(aggregate_id=sid, session_id=sid, campaign_id=cid, summary=summary)


def test_redelivered_session_end_projects_one_milestone(
    analytics_service: AnalyticsService,
) -> None:
    """A redelivered SessionEnded message adds no second milestone row.

    The second message is published after the redelivery. The stream keeps order, so once its
    milestone appears, the redelivered message has already been projected.
    """
    cid, sid = str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as client:
        analytics_service.publish(SESSION_STREAM, _session_ended(sid, cid, "first"))
        assert wait_until(
            lambda: _session_end_descriptions(client, cid) == ["first"], timeout_s=10.0
        )

        analytics_service.redeliver(SESSION_STREAM)
        analytics_service.publish(SESSION_STREAM, _session_ended(sid, cid, "second"))

        assert wait_until(
            lambda: "second" in _session_end_descriptions(client, cid), timeout_s=10.0
        )
        assert _session_end_descriptions(client, cid) == ["first", "second"]


def test_redelivery_after_restart_projects_one_milestone(
    analytics_service: AnalyticsService,
) -> None:
    """A message projected before a restart is not projected again when it is redelivered."""
    cid, sid = str(uuid4()), str(uuid4())
    analytics_service.grant_view(cid)

    with analytics_service.start() as first:
        analytics_service.publish(SESSION_STREAM, _session_ended(sid, cid, "first"))
        assert wait_until(
            lambda: _session_end_descriptions(first, cid) == ["first"], timeout_s=10.0
        )

    with analytics_service.start() as second:
        analytics_service.redeliver(SESSION_STREAM)
        analytics_service.publish(SESSION_STREAM, _session_ended(sid, cid, "second"))

        assert wait_until(
            lambda: "second" in _session_end_descriptions(second, cid), timeout_s=10.0
        )
        assert _session_end_descriptions(second, cid) == ["first", "second"]
