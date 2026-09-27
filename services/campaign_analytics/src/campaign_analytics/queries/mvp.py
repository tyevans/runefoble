"""Combatant performance scoring, damage/healing metrics, and MVP award calculations.

Governed by:
- ADR-0003: UV Monorepo Workspace for Python BCs
- Hard Invariant 6: File length limit (< 120 lines)
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from campaign_analytics.models import (
    CampaignMvpResponse,
    CombatantPerformance,
    MvpAward,
)

METRIC_FIELDS = (
    "damage_dealt",
    "damage_taken",
    "healing_provided",
    "critical_hits",
    "fumbles",
    "turns_taken",
)


def _award(title: str, c: CombatantPerformance, metric: str, score: int, desc: str) -> MvpAward:
    return MvpAward(
        title=title,
        recipient_id=c.combatant_id,
        recipient_name=c.combatant_name,
        metric_name=metric,
        score=score,
        description=desc,
    )


def calculate_mvp_rankings(
    combatants_map: dict[str, dict[str, Any]],
    campaign_id: str,
    session_id: str | None = None,
    encounter_id: str | None = None,
    matches_fn: Callable[[str, str, str], bool] | None = None,
) -> CampaignMvpResponse:
    """Query combatant MVP rankings and awards."""
    filtered = [
        v
        for v in combatants_map.values()
        if (
            matches_fn(v["campaign_id"], v["session_id"], campaign_id)
            if matches_fn
            else (v["campaign_id"] == campaign_id or v["session_id"] == campaign_id)
        )
        and (not session_id or v["session_id"] == session_id)
        and (not encounter_id or v.get("encounter_id") == encounter_id)
    ]

    def _score(v: dict[str, Any]) -> float:
        return (
            v["damage_dealt"] * 1.0
            + v["healing_provided"] * 1.5
            + v["critical_hits"] * 10.0
            - v["fumbles"] * 5.0
            + v["turns_taken"] * 2.0
        )

    combatants = [
        CombatantPerformance(
            combatant_id=v["combatant_id"],
            combatant_name=v["combatant_name"] or v["combatant_id"],
            mvp_score=round(_score(v), 1),
            **{f: v.get(f, 0) for f in METRIC_FIELDS},
        )
        for v in filtered
    ]
    combatants.sort(key=lambda c: c.mvp_score, reverse=True)

    award_specs = [
        ("Most Lethal", "damage_dealt", "Dealt {s} total combat damage"),
        ("Guardian Angel", "healing_provided", "Restored {s} party hit points"),
        ("Nat 20 Master", "critical_hits", "Landed {s} critical strikes"),
    ]
    awards = [
        _award(t, top, m, int(getattr(top, m)), d.format(s=getattr(top, m)))
        for t, m, d in award_specs
        if combatants
        and (top := max(combatants, key=lambda c: getattr(c, m)))
        and getattr(top, m) > 0
    ]

    overall_mvp = (
        _award(
            "Encounter MVP",
            combatants[0],
            "mvp_score",
            int(combatants[0].mvp_score),
            f"Highest combat efficacy ({combatants[0].mvp_score} pts)",
        )
        if combatants and combatants[0].mvp_score > 0
        else None
    )

    return CampaignMvpResponse(
        campaign_id=campaign_id,
        session_id=session_id,
        encounter_id=encounter_id,
        overall_mvp=overall_mvp,
        awards=awards,
        combatants=combatants,
    )
