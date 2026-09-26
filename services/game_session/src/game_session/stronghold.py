"""Party Stronghold, campsite facilities, and resting boons aggregate.

Part of TASK-0100 / PRD-0014 / US-0044.
Governed by Hard Invariant 2: State changes flow strictly through DeclarativeAggregate.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from pydantic import BaseModel, Field
from runefoble_events.events import StrongholdCreated, StrongholdUpgraded

FACILITY_TIERS: dict[str, dict[int, dict[str, Any]]] = {
    "watchtower": {
        1: {
            "name": "Reinforced Watchtower",
            "cost_gold": 100,
            "cost_materials": {"wood": 20},
            "boon": "Vigilant Sentry (+2 Passive Perception)",
        },
        2: {
            "name": "Fortified Spire",
            "cost_gold": 250,
            "cost_materials": {"stone": 50},
            "boon": "Vantage Scouting (Advantage on Initiative)",
        },
        3: {
            "name": "Citadel Bastion",
            "cost_gold": 500,
            "cost_materials": {"stone": 100, "iron": 40},
            "boon": "Impenetrable Ramparts (Ambush Immunity)",
        },
    },
    "herbal_rack": {
        1: {
            "name": "Herbal Drying Rack",
            "cost_gold": 75,
            "cost_materials": {"flora": 15},
            "boon": "Restorative Brews (+1d4 Rest Healing)",
        },
        2: {
            "name": "Apothecary Laboratory",
            "cost_gold": 200,
            "cost_materials": {"glass": 40},
            "boon": "Alchemical Affinity (+15% Crafting Stability)",
        },
        3: {
            "name": "Botanical Conservatory",
            "cost_gold": 450,
            "cost_materials": {"crystal": 30, "flora": 50},
            "boon": "Reagent Harvest (Free Rare Reagent)",
        },
    },
    "arcane_forge": {
        1: {
            "name": "Field Forge",
            "cost_gold": 150,
            "cost_materials": {"iron": 30},
            "boon": "Honed Blades (+1 Weapon Damage on first encounter)",
        },
        2: {
            "name": "Runic Anvil",
            "cost_gold": 350,
            "cost_materials": {"iron": 60, "mithral": 10},
            "boon": "Reinforced Armor (+1 AC for first encounter)",
        },
        3: {
            "name": "Masterwork Foundry",
            "cost_gold": 700,
            "cost_materials": {"adamantine": 20, "mithral": 30},
            "boon": "Artisan Mastery (Equipment Infusions)",
        },
    },
}


class StrongholdState(BaseModel):
    """Event-sourced state for persistent campsite and stronghold progression."""

    campaign_id: UUID | str = ""
    name: str = "Party Campsite"
    location: str = "Wilderness"
    facilities: dict[str, int] = Field(
        default_factory=lambda: {"watchtower": 0, "herbal_rack": 0, "arcane_forge": 0}
    )
    treasury_gold: int = 0
    stored_materials: dict[str, int] = Field(default_factory=dict)
    unlocked_boons: list[str] = Field(default_factory=list)
    upgrade_history: list[dict[str, Any]] = Field(default_factory=list)


class StrongholdAggregate(DeclarativeAggregate[StrongholdState]):
    """Event-sourced aggregate managing party campsite fortifications, upgrades, and resting boons."""

    aggregate_type = "Stronghold"
    requires_creation_event = False

    def __init__(self, aggregate_id: Any = None, **kwargs: Any) -> None:
        super().__init__(aggregate_id=aggregate_id, **kwargs)
        if self._state is None:
            self._state = StrongholdState(campaign_id=str(aggregate_id or ""))

    @handles(StrongholdCreated)
    def handle_created(self, event: StrongholdCreated) -> None:
        self._state = StrongholdState(
            campaign_id=event.campaign_id,
            name=event.name,
            location=event.location,
        )

    @handles(StrongholdUpgraded)
    def handle_upgraded(self, event: StrongholdUpgraded) -> None:
        if self._state is None:
            self._state = StrongholdState(campaign_id=event.campaign_id)
        self.state.campaign_id = event.campaign_id
        self.state.facilities[event.facility_id] = event.new_tier
        self.state.treasury_gold += event.gold_spent
        for mat, qty in event.materials_spent.items():
            self.state.stored_materials[mat] = self.state.stored_materials.get(mat, 0) + qty
        for b in event.unlocked_boons:
            if b not in self.state.unlocked_boons:
                self.state.unlocked_boons.append(b)
        self.state.upgrade_history.append(
            {
                "facility_id": event.facility_id,
                "new_tier": event.new_tier,
                "gold_spent": event.gold_spent,
                "materials_spent": event.materials_spent,
                "unlocked_boons": event.unlocked_boons,
            }
        )

    def create_stronghold(
        self,
        campaign_id: UUID | str,
        name: str = "Party Campsite",
        location: str = "Wilderness",
    ) -> None:
        """Initialize party base camp."""
        camp_uuid = None
        if campaign_id:
            try:
                camp_uuid = UUID(str(campaign_id))
            except Exception:
                camp_uuid = None
        self.create_event(
            StrongholdCreated,
            campaign_id=camp_uuid,
            name=name,
            location=location,
        )

    def upgrade_facility(
        self,
        facility_id: str,
        gold_spent: int = 0,
        materials_spent: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Upgrade a facility to the next tier and unlock mechanical resting boons."""
        if facility_id not in FACILITY_TIERS:
            raise ValueError(
                f"Unknown facility '{facility_id}'. Valid: {list(FACILITY_TIERS.keys())}"
            )

        current_tier = self.state.facilities.get(facility_id, 0)
        next_tier = current_tier + 1
        if next_tier > 3:
            raise ValueError(f"Facility '{facility_id}' has already reached maximum tier 3")

        tier_info = FACILITY_TIERS[facility_id][next_tier]
        spent_mats = materials_spent or tier_info["cost_materials"]
        spent_gold = gold_spent if gold_spent > 0 else tier_info["cost_gold"]
        unlocked_boon = tier_info["boon"]

        camp_uuid = None
        target_id = self.state.campaign_id or str(self.aggregate_id)
        if target_id:
            try:
                camp_uuid = UUID(str(target_id))
            except Exception:
                camp_uuid = None

        self.create_event(
            StrongholdUpgraded,
            campaign_id=camp_uuid,
            facility_id=facility_id,
            new_tier=next_tier,
            gold_spent=spent_gold,
            materials_spent=spent_mats,
            unlocked_boons=[unlocked_boon],
        )

        return {
            "facility_id": facility_id,
            "new_tier": next_tier,
            "tier_name": tier_info["name"],
            "gold_spent": spent_gold,
            "materials_spent": spent_mats,
            "unlocked_boon": unlocked_boon,
        }

    def get_active_boons(self) -> list[str]:
        """Return all active resting boons granted by current facility tiers."""
        boons = []
        for fac, tier in self.state.facilities.items():
            if tier > 0 and fac in FACILITY_TIERS:
                for t in range(1, tier + 1):
                    boon = FACILITY_TIERS[fac][t]["boon"]
                    if boon not in boons:
                        boons.append(boon)
        return boons


__all__ = [
    "FACILITY_TIERS",
    "StrongholdAggregate",
    "StrongholdState",
]
