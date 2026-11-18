"""Autonomous DM scene generation, encounter spawning, and narration routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from runefoble_events.events import (
    AutonomousActionResolved,
    EncounterSpawned,
    SceneAtmosphereSet,
)
from runefoble_platform.event_publish import publish_or_fail
from the_watcher.dependencies import (
    INFERENCE_URL,
    STREAM_WATCHER,
    autonomous_dm_engine,
    get_event_bus,
    logger,
    require_session_permission,
)
from the_watcher.identity import CallerId, get_caller_principal
from the_watcher.models import (
    DMGuidanceRequest,
    DMNarrationResult,
    EncounterSpawnRequest,
    NpcTurnRequest,
    SceneGenerateRequest,
)
from the_watcher.worker_client import call_worker

router = APIRouter(dependencies=[Depends(get_caller_principal)], tags=["autonomous_dm"])


@router.post("/api/v1/watcher/scenes/generate", response_model=SceneAtmosphereSet)
async def generate_scene(caller_id: CallerId, req: SceneGenerateRequest) -> SceneAtmosphereSet:
    """Generate dynamic scene atmosphere, location details, lighting, and ambient audio prompt."""
    await require_session_permission(caller_id, req.session_id, "session.control")
    event = autonomous_dm_engine.set_scene(
        session_id=req.session_id,
        location_type=req.location_type,
        mood=req.mood,
    )
    bus = get_event_bus()
    await publish_or_fail(bus, STREAM_WATCHER, event)
    return event


@router.post("/api/v1/watcher/encounters/spawn", response_model=EncounterSpawned)
async def spawn_encounter(caller_id: CallerId, req: EncounterSpawnRequest) -> EncounterSpawned:
    """Calculate balanced encounter and spawn tactical monsters with combat objectives."""
    await require_session_permission(caller_id, req.session_id, "session.control")
    event = autonomous_dm_engine.spawn_encounter(
        session_id=req.session_id,
        scene_id=req.scene_id,
        party_level=req.party_level,
        party_size=req.party_size,
        difficulty=req.difficulty,
    )
    bus = get_event_bus()
    await publish_or_fail(bus, STREAM_WATCHER, event)
    return event


@router.post("/api/v1/watcher/encounters/npc-turn", response_model=AutonomousActionResolved)
async def execute_npc_turn(caller_id: CallerId, req: NpcTurnRequest) -> AutonomousActionResolved:
    """Adjudicate tactical combat decision tree for an NPC or monster in an encounter."""
    await require_session_permission(caller_id, req.session_id, "session.control")
    event = autonomous_dm_engine.resolve_npc_turn(
        session_id=req.session_id,
        encounter_id=req.encounter_id,
        actor_name=req.actor_name,
        targets=req.targets,
        round_number=req.round_number,
    )
    bus = get_event_bus()
    await publish_or_fail(bus, STREAM_WATCHER, event)
    return event


@router.post("/api/v1/watcher/narrate", response_model=DMNarrationResult)
async def narrate_scene(caller_id: CallerId, req: DMGuidanceRequest) -> DMNarrationResult:
    """Autonomous DM scene description and event resolution.

    The narration comes only from the inference worker. Without a configured worker, or when
    the worker fails, the route returns HTTP 503. It never returns canned narrative text.
    """
    await require_session_permission(caller_id, req.session_id, "session.control")
    if not INFERENCE_URL:
        logger.error("RUNEFOBLE_INFERENCE_URL is not set. Scene narration has no backend.")
        raise HTTPException(
            status_code=503,
            detail={"error": "backend_unavailable", "backend": "inference_worker"},
        )
    data = await call_worker(
        INFERENCE_URL,
        "/inference/v1/dm-narration",
        {
            "campaign_id": req.campaign_id,
            "session_id": req.session_id,
            "scene_environment": req.scene_environment,
            "tone": req.tone,
            "guidance_prompt": req.prompt,
        },
        timeout=10.0,
    )
    return DMNarrationResult(
        session_id=req.session_id,
        narrative=data["narration"],
        sensory_details=data["sensory_details"],
        suggested_dm_prompts=data["suggested_dm_prompts"],
        tension_level=data["tension_level"],
        source=data["source"],
        degraded=data["degraded"],
    )
