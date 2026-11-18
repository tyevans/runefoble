"""Spatial grid aggregation queries and damage heatmap calculations.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- Hard Invariant 6: File length limit (< 500 lines)
"""

from __future__ import annotations

from typing import Any

from campaign_analytics.models import CampaignHeatmapResponse, HeatmapCell


def query_spatial_heatmap(
    spatial_records: list[dict[str, Any]],
    campaign_id: str,
    session_id: str | None = None,
    cell_size: int = 5,
    metric: str = "all",
) -> CampaignHeatmapResponse:
    """Bucket spatial rows into heatmap cells and total their density."""
    cell_size = max(1, cell_size)
    filtered = list(spatial_records)

    if metric in ("damage", "hit"):
        filtered = [r for r in filtered if r["event_type"] in ("damage", "knockout")]
    elif metric == "movement":
        filtered = [r for r in filtered if r["event_type"] == "movement"]

    buckets: dict[tuple[int, int], dict[str, int]] = {}
    for r in filtered:
        bx, by = (r["x"] // cell_size) * cell_size, (r["y"] // cell_size) * cell_size
        cell = buckets.setdefault(
            (bx, by),
            {
                "density": 0,
                "movement_count": 0,
                "damage_total": 0,
                "hit_count": 0,
                "knockout_count": 0,
            },
        )
        etype, dmg = r["event_type"], r["damage"]
        if etype == "movement":
            cell["movement_count"] += 1
            cell["density"] += 1
        elif etype == "damage":
            cell["damage_total"] += dmg
            cell["hit_count"] += 1
            cell["density"] += max(1, dmg // 5)
        elif etype == "knockout":
            cell["knockout_count"] += 1
            cell["density"] += 5

    cells = [
        HeatmapCell(
            x=bx,
            y=by,
            density=d["density"],
            movement_count=d["movement_count"],
            damage_total=d["damage_total"],
            hit_count=d["hit_count"],
            knockout_count=d["knockout_count"],
        )
        for (bx, by), d in sorted(buckets.items())
    ]
    max_density = max((c.density for c in cells), default=0)

    return CampaignHeatmapResponse(
        campaign_id=campaign_id,
        session_id=session_id,
        cell_size=cell_size,
        metric=metric,
        total_points=len(filtered),
        max_density=max_density,
        cells=cells,
    )
