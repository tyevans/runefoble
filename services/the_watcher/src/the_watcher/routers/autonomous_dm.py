"""Autonomous DM scene generation, encounter spawning, and narration routes."""

from __future__ import annotations

import httpx
from fastapi import APIRouter
from runefoble_events.events import (
    AutonomousActionResolved,
    EncounterSpawned,
    SceneAtmosphereSet,
)
from the_watcher.dependencies import (
    INFERENCE_URL,
    STREAM_WATCHER,
    autonomous_dm_engine,
    get_event_bus,
    logger,
)
from the_watcher.models import (
    DMGuidanceRequest,
    EncounterSpawnRequest,
    NpcTurnRequest,
    SceneGenerateRequest,
)

router = APIRouter(tags=["autonomous_dm"])


@router.post("/api/v1/watcher/scenes/generate", response_model=SceneAtmosphereSet)
async def generate_scene(req: SceneGenerateRequest) -> SceneAtmosphereSet:
    """Generate dynamic scene atmosphere, location details, lighting, and ambient audio prompt."""
    event = autonomous_dm_engine.set_scene(
        session_id=req.session_id,
        location_type=req.location_type,
        mood=req.mood,
    )
    bus = get_event_bus()
    try:
        await bus.publish_event(STREAM_WATCHER, event)
    except Exception as e:
        logger.warning(
            "Failed to publish SceneAtmosphereSet event to Redis stream '%s': %s",
            STREAM_WATCHER,
            e,
        )
    return event


@router.post("/api/v1/watcher/encounters/spawn", response_model=EncounterSpawned)
async def spawn_encounter(req: EncounterSpawnRequest) -> EncounterSpawned:
    """Calculate balanced encounter and spawn tactical monsters with combat objectives."""
    event = autonomous_dm_engine.spawn_encounter(
        session_id=req.session_id,
        scene_id=req.scene_id,
        party_level=req.party_level,
        party_size=req.party_size,
        difficulty=req.difficulty,
    )
    bus = get_event_bus()
    try:
        await bus.publish_event(STREAM_WATCHER, event)
    except Exception as e:
        logger.warning(
            "Failed to publish EncounterSpawned event to Redis stream '%s': %s",
            STREAM_WATCHER,
            e,
        )
    return event


@router.post("/api/v1/watcher/encounters/npc-turn", response_model=AutonomousActionResolved)
async def execute_npc_turn(req: NpcTurnRequest) -> AutonomousActionResolved:
    """Adjudicate tactical combat decision tree for an NPC or monster in an encounter."""
    event = autonomous_dm_engine.resolve_npc_turn(
        session_id=req.session_id,
        encounter_id=req.encounter_id,
        actor_name=req.actor_name,
        targets=req.targets,
        round_number=req.round_number,
    )
    bus = get_event_bus()
    try:
        await bus.publish_event(STREAM_WATCHER, event)
    except Exception as e:
        logger.warning(
            "Failed to publish AutonomousActionResolved event to Redis stream '%s': %s",
            STREAM_WATCHER,
            e,
        )
    return event


@router.post("/api/v1/watcher/narrate")
async def narrate_scene(req: DMGuidanceRequest):
    """Autonomous DM scene description and event resolution."""
    if INFERENCE_URL:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{INFERENCE_URL}/inference/v1/dm-narration",
                    json={
                        "campaign_id": "current-campaign",
                        "session_id": req.session_id,
                        "scene_environment": "Dungeon chamber",
                        "tone": "dark_fantasy",
                        "guidance_prompt": req.prompt,
                    },
                )
                if res.status_code == 200:
                    data = res.json()
                    return {
                        "session_id": req.session_id,
                        "narrative": data.get("narration"),
                        "sensory_details": data.get("sensory_details", []),
                        "suggested_dm_prompts": data.get("suggested_dm_prompts", []),
                        "tension_level": data.get("tension_level", "rising"),
                    }
        except Exception as e:
            logger.warning("Inference worker failed: %s. Falling back to local engine.", e)

    return {
        "session_id": req.session_id,
        "narrative": f"The shadows lengthen. {req.prompt}. An ominous chill fills the chamber as fate shifts.",
        "tone": "suspenseful",
    }
