"""Domain handlers and calculation helpers for West Marches aggregate state.

Part of TASK-0205 / ADR-0003 / ADR-0007 / ADR-0011.
Governed by Hard Invariant 6 (File length strictly < 130 lines).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_RAW = (
    "alchemical_workshop:Reagent Extraction (+1 Herbal Reagent);Enhanced Potion Yield (+1 Potion);Volatile Mishap Immunity\n"
    "watchtower:Early Warning (+1 Initiative);Scouting Advantage (No Ambush);Regional Threat Detection\n"
    "trading_post:Market Access;Wholesale Discounts (10% Gold);Exotic Caravan Trading\n"
    "arcane_forge:Apprentice Smithing;Enchanted Weaponry (+1 Damage);Masterwork Artifice\n"
    "herbal_rack:Campfire Herb Drying;+2 HP Rest Recovery;Restorative Salve Stock"
)
FACILITY_BOONS: dict[str, dict[int, str]] = {
    line.split(":")[0]: {i + 1: b for i, b in enumerate(line.split(":")[1].split(";"))}
    for line in _RAW.splitlines()
}


def calculate_boons(facs: dict[str, int]) -> list[str]:
    """Calculate unlocked party boons from outpost facility levels."""
    return [
        FACILITY_BOONS[f][t]
        for f, tier in facs.items()
        if f in FACILITY_BOONS
        for t in range(1, tier + 1)
        if t in FACILITY_BOONS[f]
    ]


def calculate_defensive_buffer(facs: dict[str, int], level: int = 1) -> int:
    """Calculate defensive buffer rating from watchtower tier and outpost level."""
    return facs.get("watchtower", 0) * 10 + level * 5


def _enrich_outpost(d: dict[str, Any]) -> dict[str, Any]:
    f, lvl = d["facilities"], d.get("level", 1)
    d["boons"] = calculate_boons(f)
    d["defensive_buffer"] = calculate_defensive_buffer(f, lvl)
    return d


def build_default_outpost(cid: str) -> dict[str, Any]:
    """Construct initial communal stronghold state for a newly linked frontier."""
    return _enrich_outpost(
        {
            "outpost_id": f"outpost_{cid[:8]}",
            "name": "Communal Frontier Stronghold",
            "region": "The Untamed Wilds",
            "level": 1,
            "facilities": {"alchemical_workshop": 1, "watchtower": 1, "trading_post": 1},
            "contributing_campaigns": [cid],
            "stored_resources": {"gold": 100, "timber": 20, "stone": 15},
        }
    )


def build_discovery_entry(event: Any) -> dict[str, Any]:
    """Construct a discovery pin dictionary from a CrossCampaignDiscoveryShared event."""
    ts = getattr(event, "occurred_at", None)
    f = ["discovery_id", "name", "discovery_type", "coordinates"]
    f += ["discovered_by_party_name", "description", "danger_level", "metadata"]
    d = {k: getattr(event, k) for k in f}
    d["discovered_by_campaign_id"] = str(event.discovered_by_campaign_id)
    d["timestamp"] = ts.isoformat() if ts else datetime.now(UTC).isoformat()
    return d


def build_notice_entry(event: Any) -> dict[str, Any]:
    """Construct a notice entry dictionary from a CommunalNoticePosted event."""
    f = ["notice_id", "author_name", "title", "content", "notice_type", "bounty_reward"]
    d = {k: getattr(event, k) for k in f}
    d["campaign_id"], d["posted_at"] = str(event.campaign_id), datetime.now(UTC).isoformat()
    return d


def apply_discovery(disc: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Deduplicate and append discovery pin to world state."""
    return [d for d in disc if d.get("discovery_id") != entry.get("discovery_id")] + [entry]


def apply_outpost_established(outposts: dict[str, dict[str, Any]], event: Any) -> None:
    """Mutate outposts mapping when a new frontier outpost is established."""
    outposts[event.outpost_id] = _enrich_outpost(
        {
            "outpost_id": event.outpost_id,
            "name": event.name,
            "region": event.region,
            "level": event.level,
            "facilities": event.facilities or {"watchtower": 1, "trading_post": 1},
            "contributing_campaigns": [str(event.contributing_campaign_id)],
            "stored_resources": dict(event.resources_contributed or {}),
        }
    )


def apply_outpost_upgraded(outposts: dict[str, dict[str, Any]], event: Any) -> None:
    """Mutate outpost state when a facility tier upgrade is applied."""
    if event.outpost_id not in outposts:
        return
    out = outposts[event.outpost_id]
    out["facilities"][event.facility_id] = event.new_tier
    cid = str(event.contributing_campaign_id)
    if cid and cid not in out["contributing_campaigns"]:
        out["contributing_campaigns"].append(cid)
    for m, q in event.materials_spent.items():
        out["stored_resources"][m] = out["stored_resources"].get(m, 0) + q
    _enrich_outpost(out)


def evaluate_territory_claim(
    coordinates: dict[str, float], existing: dict[str, dict[str, Any]], min_dist: float = 10.0
) -> bool:
    """Evaluate whether a new outpost location conflicts with existing outpost claims."""
    x, y = coordinates.get("x", 0.0), coordinates.get("y", 0.0)
    for out in existing.values():
        ox, oy = out.get("coordinates", {}).get("x", 0.0), out.get("coordinates", {}).get("y", 0.0)
        if (ox or oy) and ((x - ox) ** 2 + (y - oy) ** 2) ** 0.5 < min_dist:
            return False
    return True
