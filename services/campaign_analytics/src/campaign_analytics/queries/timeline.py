"""Chronicle timeline milestone queries and session event filtering.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- Hard Invariant 6: File length limit (< 500 lines)
"""

from __future__ import annotations

import json
from typing import Any

from campaign_analytics.models import (
    CampaignTimelineResponse,
    TimelineMilestone,
)


def query_campaign_timeline(
    milestones: list[dict[str, Any]],
    campaign_id: str,
    session_id: str | None = None,
    limit: int = 50,
) -> CampaignTimelineResponse:
    """Order milestone rows chronologically and return the first `limit` of them."""
    filtered = sorted(milestones, key=lambda m: m["timestamp"])
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
            metadata=json.loads(m["metadata_json"] or "{}"),
        )
        for m in selected
    ]
    return CampaignTimelineResponse(
        campaign_id=campaign_id,
        session_id=session_id,
        total_milestones=len(filtered),
        milestones=milestone_objects,
    )
