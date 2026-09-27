"""Chronicle timeline milestone queries and session event filtering.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- Hard Invariant 6: File length limit (< 110 lines)
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from campaign_analytics.models import (
    CampaignTimelineResponse,
    TimelineMilestone,
)


def create_milestone_record(
    campaign_id: str,
    session_id: str,
    milestone_type: str,
    title: str,
    description: str,
    timestamp: str | None = None,
    metadata_dict: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build milestone in-memory record and database insert dictionary."""
    meta = metadata_dict or {}
    ts = timestamp or datetime.now(UTC).isoformat()
    mid = str(uuid4())
    rec = {
        "id": mid,
        "campaign_id": str(campaign_id),
        "session_id": str(session_id),
        "milestone_type": milestone_type,
        "title": title,
        "description": description,
        "timestamp": ts,
        "metadata": meta,
    }
    vals = {
        "id": mid,
        "campaign_id": str(campaign_id),
        "session_id": str(session_id),
        "milestone_type": milestone_type,
        "title": title,
        "description": description,
        "timestamp": ts,
        "metadata_json": json.dumps(meta),
    }
    return rec, vals


def query_campaign_timeline(
    milestones: list[dict[str, Any]],
    campaign_id: str,
    session_id: str | None = None,
    limit: int = 50,
    matches_fn: Callable[[str, str, str], bool] | None = None,
) -> CampaignTimelineResponse:
    """Query chronological event milestones linking session recaps and boss encounters."""
    filtered = [
        m
        for m in milestones
        if (
            matches_fn(m["campaign_id"], m["session_id"], campaign_id)
            if matches_fn
            else (m["campaign_id"] == campaign_id or m["session_id"] == campaign_id)
        )
        and (not session_id or m["session_id"] == session_id)
    ]

    filtered.sort(key=lambda m: m["timestamp"])
    selected = filtered[:limit]
    milestone_objects = [
        TimelineMilestone(
            id=m["id"],
            campaign_id=m["campaign_id"],
            session_id=m["session_id"],
            type=m["milestone_type"],
            title=m["title"],
            description=m["description"],
            timestamp=m["timestamp"],
            metadata=m.get("metadata", {}),
        )
        for m in selected
    ]
    return CampaignTimelineResponse(
        campaign_id=campaign_id,
        session_id=session_id,
        total_milestones=len(filtered),
        milestones=milestone_objects,
    )
