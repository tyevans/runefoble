"""Skirmish adjudication engine evaluating military strength, terrain advantages, and casualties."""

from __future__ import annotations

import random
from uuid import uuid4

from the_watcher.turf_war.models import SkirmishOutcome, SkirmishSimulateRequest

TERRAIN_DEFENSIVE_MODIFIERS: dict[str, int] = {
    "plains": 0,
    "hills": 3,
    "forest": 2,
    "urban": 4,
    "swamp": 3,
    "mountain": 5,
    "fortress": 7,
}


class SkirmishEngine:
    """Calculates tactical military skirmish resolutions and casualty distributions."""

    def resolve(self, req: SkirmishSimulateRequest) -> SkirmishOutcome:
        """Resolve a boundary clash between two factions based on terrain and strength."""
        atk_roll = req.attacker_roll if req.attacker_roll is not None else random.randint(1, 20)
        def_roll = req.defender_roll if req.defender_roll is not None else random.randint(1, 20)
        terrain_mod = TERRAIN_DEFENSIVE_MODIFIERS.get(req.terrain.lower(), 1)

        atk_score = req.attacker.military_strength + req.attacker.morale_modifier + atk_roll
        def_score = (
            req.defender.military_strength
            + req.defender.defense_rating
            + terrain_mod
            + req.defender.morale_modifier
            + def_roll
        )

        skirmish_id = f"skm-{uuid4().hex[:8]}"

        if atk_score > def_score:
            margin = atk_score - def_score
            winner = req.attacker.faction_id
            loser = req.defender.faction_id
            territory_captured = margin >= 3
            def_casualties = min(
                req.defender.military_strength,
                max(1, int(req.defender.military_strength * 0.15 + margin * 0.5)),
            )
            atk_casualties = min(
                req.attacker.military_strength,
                max(0, int(req.attacker.military_strength * 0.10 - margin * 0.1)),
            )
            narrative = (
                f"{winner} launched an assault on {req.contested_node} ({req.terrain}) and overran "
                f"{loser}'s defenses with margin +{margin}. "
                + (
                    "Territory was successfully captured!"
                    if territory_captured
                    else "The defensive line was compromised but remains contested."
                )
            )
            is_stalemate = False
        elif def_score > atk_score:
            margin = def_score - atk_score
            winner = req.defender.faction_id
            loser = req.attacker.faction_id
            territory_captured = False
            atk_casualties = min(
                req.attacker.military_strength,
                max(1, int(req.attacker.military_strength * 0.15 + margin * 0.5)),
            )
            def_casualties = min(
                req.defender.military_strength,
                max(0, int(req.defender.military_strength * 0.10 - margin * 0.1)),
            )
            narrative = (
                f"{winner} fortified {req.contested_node} ({req.terrain}) and repelled {loser}'s assault "
                f"with margin +{margin}. Territorial control was maintained."
            )
            is_stalemate = False
        else:
            winner = req.defender.faction_id
            loser = req.attacker.faction_id
            territory_captured = False
            is_stalemate = True
            atk_casualties = max(1, int(req.attacker.military_strength * 0.08))
            def_casualties = max(1, int(req.defender.military_strength * 0.08))
            narrative = (
                f"A bloody stalemate erupted at {req.contested_node} ({req.terrain}) between "
                f"{req.attacker.faction_id} and {req.defender.faction_id}. Control remains unchanged."
            )

        total_cas = atk_casualties + def_casualties
        unrest_delta = min(50, max(5, int(total_cas * 0.5 + (12 if territory_captured else 6))))

        return SkirmishOutcome(
            skirmish_id=skirmish_id,
            winner_faction_id=winner,
            loser_faction_id=loser,
            is_stalemate=is_stalemate,
            territory_captured=territory_captured,
            attacker_casualties=atk_casualties,
            defender_casualties=def_casualties,
            unrest_delta=unrest_delta,
            narrative=narrative,
        )


skirmish_engine = SkirmishEngine()
