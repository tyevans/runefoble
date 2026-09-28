"""Social relationship graph algorithms, tension metrics, and operations projections.

Governed by ADR-0002, ADR-0007, and PRD-0024.
"""

from __future__ import annotations

from typing import Any

from game_session.settlement.worker_models import (
    NPCWorkerState,
)


def compute_worker_tension(
    worker: NPCWorkerState, peers: list[NPCWorkerState] | None = None
) -> float:
    """Compute normalized interpersonal tension [0.0 - 1.0] from relationships and traits."""
    tension = 0.1
    peer_ids = {p.npc_id for p in peers or [] if p.npc_id != worker.npc_id}

    for rel in worker.relationships:
        rel_type = rel.relation_type.lower()
        intensity = max(0.1, abs(rel.intensity))
        is_peer = rel.target_npc_id in peer_ids

        if rel_type in ("rival", "enemy", "nemesis"):
            tension += (0.4 if is_peer else 0.25) * intensity
        elif rel_type in ("debtor", "creditor"):
            tension += (0.3 if is_peer else 0.15) * intensity
        elif rel_type in ("ally", "lover", "mentor", "friend"):
            tension -= (0.2 if is_peer else 0.1) * intensity

    tension += 0.2 * (worker.traits.neuroticism - 0.5)
    tension -= 0.15 * (worker.traits.agreeableness - 0.5)
    return round(min(1.0, max(0.0, tension)), 2)


def compute_supply_chain_dependencies(worker: NPCWorkerState) -> list[dict[str, Any]]:
    """Compute supply chain and resource dependencies from worker relationships."""
    deps: list[dict[str, Any]] = []
    for rel in worker.relationships:
        if (
            rel.relation_type in ("supplier", "debtor", "apprentice")
            or "resource" in rel.metadata
            or "supply" in rel.metadata
        ):
            status = rel.metadata.get("supply_status", "flowing")
            is_disrupted = (
                rel.relation_type == "rival"
                or rel.metadata.get("disrupted", False)
                or worker.mood in ("desperate", "anxious")
            )
            deps.append(
                {
                    "source_npc_id": worker.npc_id,
                    "target_npc_id": rel.target_npc_id,
                    "relation_type": rel.relation_type,
                    "resource": rel.metadata.get("resource", "raw_materials"),
                    "status": "disrupted" if is_disrupted else status,
                    "risk_level": "critical" if is_disrupted else "low",
                }
            )
    return deps


def _matches_proficiency(proficiency: str, role: str) -> bool:
    p = proficiency.lower()
    r = role.lower()
    if p in r or r in p:
        return True
    p_stem = p[:-3] if p.endswith("ing") else (p[:-2] if p.endswith("er") else p)
    r_tokens = [tok.rstrip("er").rstrip("ing") for tok in r.split()]
    return any(len(tok) >= 3 and (tok in p or p_stem in tok) for tok in r_tokens) or (
        len(p_stem) >= 3 and p_stem in r
    )


def calculate_service_quality_contribution(
    worker: NPCWorkerState, establishment_tier: int = 1
) -> float:
    """Project individual service quality contribution based on proficiency, mood, and traits."""
    base = 1.0 * max(1, establishment_tier)
    role_norm = worker.role.lower()

    if any(_matches_proficiency(p, role_norm) for p in worker.trade_proficiencies):
        base += 0.6
    elif worker.trade_proficiencies:
        base += 0.2

    base += (worker.traits.conscientiousness - 0.5) * 0.4
    base += (worker.traits.agreeableness - 0.5) * 0.3
    base -= (worker.traits.neuroticism - 0.5) * 0.2

    mood_norm = worker.mood.lower()
    if mood_norm in ("cheerful", "inspired", "ecstatic"):
        base += 0.4
    elif mood_norm in ("content", "steady", "calm"):
        base += 0.2
    elif mood_norm in ("anxious", "stressed", "weary"):
        base -= 0.3
    elif mood_norm in ("desperate", "hostile", "furious"):
        base -= 0.6

    base -= worker.interpersonal_tension * 0.4
    return round(max(0.1, base), 2)


def serialize_to_redstring_edges(worker: NPCWorkerState) -> list[dict[str, Any]]:
    """Serialize relationships to redstring-compatible knowledge graph edges."""
    edges: list[dict[str, Any]] = []
    for rel in worker.relationships:
        edges.append(
            {
                "source": worker.npc_id,
                "target": rel.target_npc_id,
                "source_id": worker.npc_id,
                "target_id": rel.target_npc_id,
                "source_name": worker.name,
                "target_name": rel.metadata.get("target_name", rel.target_npc_id),
                "relationship_type": rel.relation_type,
                "relation_type": rel.relation_type,
                "intensity": rel.intensity,
                "weight": rel.intensity,
                "confidence": 0.95,
                "metadata": {
                    "interpersonal_tension": worker.interpersonal_tension,
                    "is_supply_chain": rel.relation_type in ("supplier", "debtor", "apprentice"),
                    **rel.metadata,
                },
            }
        )
    return edges


def calculate_establishment_operations(
    base_cost: int,
    establishment_tier: int,
    workers: list[NPCWorkerState],
) -> tuple[float, str, int, int, float, float]:
    """Calculate projected service quality, tier name, wages, cost, tension, and morale."""
    active = [w for w in workers if w.status == "active"]
    if not active:
        return 1.0, "standard", 0, base_cost, 0.0, 0.5

    for w in active:
        w.interpersonal_tension = compute_worker_tension(w, active)
        w.service_quality_contribution = calculate_service_quality_contribution(
            w, establishment_tier
        )
        w.redstring_edges = serialize_to_redstring_edges(w)

    total_wages = sum(w.wage for w in active)
    net_operating_cost = base_cost + total_wages
    avg_tension = round(sum(w.interpersonal_tension for w in active) / len(active), 2)

    morale_map = {
        "cheerful": 1.0,
        "ecstatic": 1.0,
        "content": 0.8,
        "steady": 0.7,
        "anxious": 0.4,
        "desperate": 0.2,
        "hostile": 0.1,
    }
    avg_morale = round(
        sum(morale_map.get(w.mood.lower(), 0.5) for w in active) / len(active),
        2,
    )

    quality_score = round(
        min(5.0, max(0.5, sum(w.service_quality_contribution for w in active))),
        2,
    )

    if quality_score < 1.5:
        tier_name = "poor"
    elif quality_score < 2.5:
        tier_name = "standard"
    elif quality_score < 3.8:
        tier_name = "good"
    elif quality_score < 4.5:
        tier_name = "exceptional"
    else:
        tier_name = "masterwork"

    return (
        quality_score,
        tier_name,
        total_wages,
        net_operating_cost,
        avg_tension,
        avg_morale,
    )
