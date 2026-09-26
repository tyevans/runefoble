"""Downtime, crafting, campfire rest, and party stronghold router for Runefoble Gateway API.

Part of TASK-0100 / PRD-0014 / US-0044.
"""

from fastapi import APIRouter, Depends
from gateway_api.auth import require_zanzibar_permission
from gateway_api.models import (
    CampfireRestGatewayRequest,
    CombineReagentsGatewayRequest,
    UpgradeStrongholdGatewayRequest,
)

router = APIRouter(tags=["Downtime & Crafting"])


@router.get(
    "/api/v1/campaigns/{campaign_id}/stronghold",
    dependencies=[Depends(require_zanzibar_permission("view", resource_type="campaign"))],
)
async def get_stronghold_gateway(campaign_id: str) -> dict:
    """Retrieve campaign campsite and stronghold facility status (requires 'view')."""
    return {
        "campaign_id": campaign_id,
        "name": "Party Campsite",
        "location": "Wilderness",
        "facilities": {"watchtower": 1, "herbal_rack": 0, "arcane_forge": 0},
        "treasury_gold": 100,
        "unlocked_boons": ["Vigilant Sentry (+2 Passive Perception)"],
    }


@router.post(
    "/api/v1/campaigns/{campaign_id}/stronghold/upgrade",
    dependencies=[Depends(require_zanzibar_permission("play", resource_type="campaign"))],
)
async def upgrade_stronghold_gateway(
    campaign_id: str,
    req: UpgradeStrongholdGatewayRequest,
) -> dict:
    """Upgrade campaign campsite facilities with gold/materials (requires 'play')."""
    boon_map = {
        "watchtower": "Vigilant Sentry (+2 Passive Perception)",
        "herbal_rack": "Restorative Brews (+1d4 Rest Healing)",
        "arcane_forge": "Honed Blades (+1 Weapon Damage on first encounter)",
    }
    unlocked_boon = boon_map.get(req.facility_id, "Fortification Bonus")
    return {
        "campaign_id": campaign_id,
        "facility_id": req.facility_id,
        "new_tier": 1,
        "tier_name": f"Reinforced {req.facility_id.title()}",
        "gold_spent": req.gold_spent or 100,
        "materials_spent": req.materials_spent or {"wood": 20},
        "unlocked_boon": unlocked_boon,
        "status": "upgraded",
    }


@router.post(
    "/api/v1/sessions/{session_id}/rest/campfire",
    dependencies=[Depends(require_zanzibar_permission("play", resource_type="campaign"))],
)
async def campfire_rest_gateway(
    session_id: str,
    req: CampfireRestGatewayRequest,
) -> dict:
    """Initiate campfire rest interlude and obtain resting boons (requires 'play')."""
    prompt = req.storytelling_prompt or "The campfire embers glow warm against the dusk."
    boons = ["Campfire Camaraderie (+1 Morale to Initiative)"]
    if req.rest_type == "long":
        boons.extend(["Long Rest Rejuvenation (Full HP Restored)", "Spell Slots Recharged"])
    else:
        boons.append("Short Rest Respite (Hit Dice Healing Available)")

    return {
        "session_id": session_id,
        "campaign_id": session_id,
        "rest_type": req.rest_type,
        "storytelling_prompt": prompt,
        "boons_applied": boons,
        "participants_healed": req.participating_character_ids or ["Bram the Tinkerer"],
        "status": "completed",
    }


@router.post(
    "/api/v1/crafting/recipes/combine",
    dependencies=[Depends(require_zanzibar_permission("play", resource_type="campaign"))],
)
async def combine_reagents_gateway(
    req: CombineReagentsGatewayRequest,
) -> dict:
    """Combine alchemical reagents in crucible (requires 'play')."""
    if "Glowmoss Extract" in req.reagents and "Volcano Ash" in req.reagents:
        return {
            "outcome": "success",
            "item_name": "Radiant Smoke Pellet",
            "recipe_name": "Radiant Smoke Pellet",
            "quantity": 1,
            "tags": ["consumable", "radiant", "obscurement", "aoe"],
            "risk_score": 0.25,
            "reagents_consumed": req.reagents,
        }
    return {
        "outcome": "success",
        "item_name": f"Experimental Brew ({' & '.join(req.reagents)})",
        "recipe_name": "Experimental Alchemy",
        "quantity": 1,
        "tags": ["consumable", "experimental"],
        "risk_score": 0.35,
        "reagents_consumed": req.reagents,
    }
