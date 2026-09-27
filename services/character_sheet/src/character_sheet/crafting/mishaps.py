"""Volatile mishap tables, risk calculations, and alchemical consequence resolvers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from character_sheet.crafting.recipes import CATALYSTS_CATALOGUE, REAGENTS_CATALOGUE
from runefoble_events.events import CraftingMishapOccurred

MISHAP_TABLE: list[dict[str, Any]] = [
    {
        "mishap_type": "minor_explosion",
        "severity": "minor",
        "damage": 4,
        "condition": None,
        "description": "A sharp bang fills the laboratory! Soot covers the crucible and singes eyebrows.",
    },
    {
        "mishap_type": "caustic_fumes",
        "severity": "moderate",
        "damage": 2,
        "condition": "poisoned",
        "description": "Acrid purple vapor spills forth, burning the lungs and inducing nausea.",
    },
    {
        "mishap_type": "flashbang_stun",
        "severity": "minor",
        "damage": 0,
        "condition": "blinded",
        "description": "A sudden blinding burst of light erupts from the crucible, dazzling vision.",
    },
    {
        "mishap_type": "bubbling_sludge",
        "severity": "minor",
        "damage": 0,
        "condition": None,
        "description": "The mixture curdles into inert, foul-smelling gray sludge.",
    },
]


def calculate_volatile_risk(reagents: list[str], catalyst: str | None = None) -> float:
    """Calculate the volatility risk score (0.0 to 1.0) for a combination of reagents."""
    if not reagents:
        return 0.0

    instabilities: list[float] = []
    affinities: list[str] = []
    for r in reagents:
        spec = REAGENTS_CATALOGUE.get(r, {"instability": 0.25, "affinity": "mineral"})
        instabilities.append(spec["instability"])
        affinities.append(spec["affinity"])
        if (sec := spec.get("secondary_affinity")) and sec != "none":
            affinities.append(sec)

    base_risk = sum(instabilities) / len(instabilities)
    if "volatile" in affinities and "toxic" in affinities:
        base_risk += 0.30
    if affinities.count("volatile") >= 2:
        base_risk += 0.25
    if "radiant" in affinities and "toxic" in affinities:
        base_risk += 0.20
    if "radiant" in affinities and "botanical" in affinities:
        base_risk -= 0.15
    if "volatile" in affinities and "mineral" in affinities:
        base_risk -= 0.10

    if catalyst and catalyst in CATALYSTS_CATALOGUE:
        base_risk += CATALYSTS_CATALOGUE[catalyst]["stability_bonus"]

    return max(0.05, min(0.95, round(base_risk, 2)))


class MishapResolver:
    """Resolver for volatile alchemical mishaps, consequences, and explosion events."""

    @staticmethod
    def is_mishap(
        risk: float,
        catalyst: str | None = None,
        force_mishap: bool = False,
        risk_threshold: float = 0.50,
    ) -> bool:
        """Determine if a combination triggers a volatile reaction."""
        return force_mishap or (risk > risk_threshold and not catalyst)

    @staticmethod
    def select_mishap(risk_score: float, d100_roll: int | None = None) -> dict[str, Any]:
        """Select a mishap outcome from table based on risk score or d100 roll."""
        if d100_roll is not None:
            return MISHAP_TABLE[min(len(MISHAP_TABLE) - 1, max(0, d100_roll // 25))]
        return MISHAP_TABLE[0] if risk_score > 0.6 else MISHAP_TABLE[1]

    @staticmethod
    def event_kwargs(
        character_id: UUID,
        mishap: dict[str, Any],
        reagents: list[str],
        camp: UUID | None,
        sess: UUID | None,
        aggregate_id: Any = None,
    ) -> dict[str, Any]:
        """Build event kwargs for CraftingMishapOccurred."""
        return {
            "aggregate_id": aggregate_id or character_id,
            "character_id": character_id,
            "campaign_id": camp,
            "session_id": sess,
            "mishap_type": mishap["mishap_type"],
            "severity": mishap["severity"],
            "description": mishap["description"],
            "damage_dealt": mishap["damage"],
            "condition_inflicted": mishap["condition"],
            "reagents_lost": list(reagents),
        }

    @classmethod
    def create_mishap_event(
        cls,
        character_id: UUID,
        mishap: dict[str, Any],
        reagents: list[str],
        camp: UUID | None = None,
        sess: UUID | None = None,
    ) -> CraftingMishapOccurred:
        return CraftingMishapOccurred(
            **cls.event_kwargs(character_id, mishap, reagents, camp, sess)
        )
