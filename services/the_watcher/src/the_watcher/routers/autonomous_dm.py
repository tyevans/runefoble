"""Autonomous DM scene generation, encounter spawning, and narration routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from runefoble_events.events import (
    AutonomousActionResolved,
    EncounterSpawned,
    SceneAtmosphereSet,
)
from runefoble_platform.event_publish import publish_or_fail
from the_watcher.dependencies import (
    STREAM_WATCHER,
    autonomous_dm_engine,
    engine,
    get_event_bus,
    require_session_permission,
)
from the_watcher.engine_selection import load_watcher_ports
from the_watcher.identity import CallerId, get_caller_principal
from the_watcher.models import (
    DMGuidanceRequest,
    DMNarrationResult,
    EncounterSpawnRequest,
    NpcTurnRequest,
    SceneGenerateRequest,
)

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

    The narration comes only from the selected narrator port. A failed engine returns HTTP 503.
    The route never returns canned narrative text.
    """
    await require_session_permission(caller_id, req.session_id, "session.control")
    return await load_watcher_ports(engine).narrator.narrate(req)
