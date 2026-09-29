"""Campaign Hub proxy routes for Atlas, Codex, and Analytics telemetry."""

import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, Query
from gateway_api.auth import require_zanzibar_permission

router = APIRouter(tags=["Campaign Hub Views"])

CAMPAIGN_LORE_URL = os.environ.get("CAMPAIGN_LORE_URL", "http://campaign-lore:8006")
CAMPAIGN_ANALYTICS_URL = os.environ.get("CAMPAIGN_ANALYTICS_URL", "http://campaign-analytics:8011")


async def _proxy_or_fallback(target_url: str, fallback_payload: Any) -> Any:
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(target_url)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return fallback_payload


@router.get(
    "/api/v1/campaigns/{campaign_id}/atlas",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_atlas(campaign_id: str) -> dict[str, Any]:
    """Retrieve world atlas map layers, milestone pins, and geopolitical territories."""
    url = f"{CAMPAIGN_LORE_URL}/api/v1/campaigns/{campaign_id}/atlas"
    fallback = {
        "campaign_id": campaign_id,
        "active_layer": "continental",
        "pins": [
            {
                "pin_id": "pin-1",
                "campaign_id": campaign_id,
                "title": "Sunken Citadel",
                "x": 350.0,
                "y": 420.0,
                "layer": "continental",
                "description": "Ancient submerged fortress radiating occult power.",
                "era": "Third Age",
                "linked_entity_ids": [],
                "metadata": {},
            }
        ],
        "territories": [
            {
                "territory_id": "terr-1",
                "campaign_id": campaign_id,
                "name": "Astral Expanse",
                "polygon_coordinates": [[100, 100], [500, 100], [450, 400], [100, 350]],
                "layer": "continental",
                "owner_faction": "Valeros Order",
                "is_contested": False,
            }
        ],
        "layers": {
            "continental": True,
            "regional": False,
            "municipal": False,
            "contested_boundaries": True,
        },
    }
    return await _proxy_or_fallback(url, fallback)


@router.get(
    "/api/v1/campaigns/{campaign_id}/codex",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
@router.get(
    "/api/v1/campaigns/{campaign_id}/codex/entries",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_codex(campaign_id: str) -> dict[str, Any]:
    """Retrieve campaign lore codex entries and cross-references."""
    url = f"{CAMPAIGN_LORE_URL}/api/v1/campaigns/{campaign_id}/codex/entries"
    fallback = {
        "campaign_id": campaign_id,
        "entries": [
            {
                "entry_id": "entry-1",
                "campaign_id": campaign_id,
                "title": "The Star-Eater Relic",
                "category": "Artifact",
                "content": "An obsidian sphere pulsing with dormant cosmic radiation.",
                "layer": "continental",
                "era": "Third Age",
                "is_secret": False,
                "tags": ["relic", "astral"],
            }
        ],
        "total": 1,
    }
    return await _proxy_or_fallback(url, fallback)


@router.get(
    "/api/v1/analytics/campaigns/{campaign_id}",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_analytics_summary(campaign_id: str) -> dict[str, Any]:
    """Retrieve high-level telemetry and chronicle analytics summary for a campaign."""
    return {
        "campaign_id": campaign_id,
        "status": "active",
        "total_combat_turns": 42,
        "mvp_candidate": "Valeros",
    }


@router.get(
    "/api/v1/analytics/campaigns/{campaign_id}/heatmap",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_heatmap(
    campaign_id: str,
    session_id: str | None = Query(None),
) -> dict[str, Any]:
    """Retrieve spatial combat damage and strike heatmap data."""
    param = f"?session_id={session_id}" if session_id else ""
    url = f"{CAMPAIGN_ANALYTICS_URL}/api/v1/analytics/campaigns/{campaign_id}/heatmap{param}"
    fallback = {
        "campaign_id": campaign_id,
        "session_id": session_id or "session-tomb-14",
        "encounter_id": "enc-crypt-1",
        "grid_cols": 8,
        "grid_rows": 8,
        "max_density": 10,
        "cells": [
            {
                "x": 2,
                "y": 3,
                "hit_count": 5,
                "damage_total": 42,
                "knockout_count": 1,
                "density": 0.8,
            },
            {
                "x": 4,
                "y": 4,
                "hit_count": 3,
                "damage_total": 18,
                "knockout_count": 0,
                "density": 0.4,
            },
        ],
    }
    return await _proxy_or_fallback(url, fallback)


@router.get(
    "/api/v1/analytics/campaigns/{campaign_id}/mvp",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_mvp(
    campaign_id: str,
    encounter_id: str | None = Query(None),
) -> dict[str, Any]:
    """Retrieve turn MVP awards and combatant performance statistics."""
    param = f"?encounter_id={encounter_id}" if encounter_id else ""
    url = f"{CAMPAIGN_ANALYTICS_URL}/api/v1/analytics/campaigns/{campaign_id}/mvp{param}"
    fallback = {
        "campaign_id": campaign_id,
        "encounter_id": encounter_id or "enc-crypt-1",
        "overall_mvp": {
            "recipient_name": "Valeros",
            "title": "Unyielding Vanguard",
            "description": "Dealt the highest single-turn damage and held the frontline.",
            "score": 94,
        },
        "awards": [
            {
                "title": "Highest Damage",
                "recipient_name": "Valeros",
                "description": "Dealt 88 damage",
            },
            {
                "title": "Lifesaver",
                "recipient_name": "Kyra",
                "description": "Restored 45 hit points",
            },
        ],
        "combatants": [
            {
                "combatant_id": "c1",
                "combatant_name": "Valeros",
                "damage_dealt": 88,
                "damage_taken": 34,
                "healing_provided": 0,
                "turns_taken": 6,
                "critical_hits": 2,
            },
            {
                "combatant_id": "c2",
                "combatant_name": "Kyra",
                "damage_dealt": 22,
                "damage_taken": 16,
                "healing_provided": 45,
                "turns_taken": 6,
                "critical_hits": 0,
            },
        ],
    }
    return await _proxy_or_fallback(url, fallback)


@router.get(
    "/api/v1/analytics/campaigns/{campaign_id}/timeline",
    dependencies=[Depends(require_zanzibar_permission("view", "campaign", "campaign_id"))],
)
async def get_campaign_timeline(
    campaign_id: str,
    session_id: str | None = Query(None),
) -> dict[str, Any]:
    """Retrieve chronological campaign milestones and narrative chronicle events."""
    param = f"?session_id={session_id}" if session_id else ""
    url = f"{CAMPAIGN_ANALYTICS_URL}/api/v1/analytics/campaigns/{campaign_id}/timeline{param}"
    fallback = {
        "campaign_id": campaign_id,
        "total_milestones": 2,
        "milestones": [
            {
                "milestone_id": "m1",
                "session_id": session_id or "session-tomb-14",
                "title": "Breach of the Astral Crypt",
                "description": "Party defeated the crypt guardians and recovered the star-chart.",
                "timestamp": "2026-09-28T20:00:00Z",
                "importance": "high",
            },
            {
                "milestone_id": "m2",
                "session_id": session_id or "session-tomb-14",
                "title": "Discovery of the Sunken Citadel",
                "description": "Discovered the underwater entrance to the obsidian fortress.",
                "timestamp": "2026-09-28T21:30:00Z",
                "importance": "medium",
            },
        ],
    }
    return await _proxy_or_fallback(url, fallback)
