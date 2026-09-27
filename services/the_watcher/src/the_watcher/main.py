"""The Watcher AI Gameplay Service entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from the_watcher.dependencies import (
    INFERENCE_URL,
    STREAM_BOARD,
    STREAM_WATCHER,
    autonomous_dm_engine,
    chronicle_engine,
    compound_action_engine,
    disambiguation_engine,
    engine,
    faction_simulation_engine,
    get_event_bus,
    set_event_bus,
    to_uuid,
)
from the_watcher.models import (
    CandidateTarget,
    CompoundActionNode,
    DMGuidanceRequest,
    EncounterSpawnRequest,
    EntityTarget,
    IntentExecuteRequest,
    IntentExecuteResponse,
    IntentParseRequest,
    IntentParseResponse,
    IntentResolveRequest,
    IntentResolveResponse,
    IntentResult,
    NpcTurnRequest,
    RecapRequest,
    SceneGenerateRequest,
    SpeechInputRequest,
    StandInAction,
    StandInRecapRequest,
    StandInRecapResponse,
    StandInRequest,
)
from the_watcher.routers import (
    autonomous_dm_router,
    chronicle_router,
    copilot_router,
    faction_resources_router,
    factions_router,
    intent_router,
    stand_in_router,
)

app = FastAPI(
    title="Runefoble - The Watcher Service",
    version="0.1.0",
    description="AI Gameplay System: Speech-to-Intent, Board Animator, Autonomous DM & Missing Player Stand-in.",
)

app.include_router(intent_router)
app.include_router(autonomous_dm_router)
app.include_router(stand_in_router)
app.include_router(chronicle_router)
app.include_router(copilot_router)
app.include_router(factions_router)
app.include_router(faction_resources_router)


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "the_watcher",
        "inference_worker_url": INFERENCE_URL or "none (using local heuristic engine)",
    }


@app.get("/ui/manifest")
def get_ui_manifest():
    """Advertise vendored microfrontend components for The Watcher."""
    return {
        "service": "the_watcher",
        "package": "@runefoble/the-watcher-ui",
        "components": [
            "runefoble-watcher-feed",
            "runefoble-autonomous-dm",
            "runefoble-dm-whisper-bar",
            "runefoble-faction-radar",
        ],
        "version": "0.1.0",
    }


def main():
    import uvicorn

    uvicorn.run("the_watcher.main:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    main()

__all__ = [
    "CandidateTarget",
    "CompoundActionNode",
    "DMGuidanceRequest",
    "EncounterSpawnRequest",
    "EntityTarget",
    "INFERENCE_URL",
    "IntentExecuteRequest",
    "IntentExecuteResponse",
    "IntentParseRequest",
    "IntentParseResponse",
    "IntentResolveRequest",
    "IntentResolveResponse",
    "IntentResult",
    "NpcTurnRequest",
    "RecapRequest",
    "STREAM_BOARD",
    "STREAM_WATCHER",
    "SceneGenerateRequest",
    "SpeechInputRequest",
    "StandInAction",
    "StandInRecapRequest",
    "StandInRecapResponse",
    "StandInRequest",
    "app",
    "autonomous_dm_engine",
    "chronicle_engine",
    "compound_action_engine",
    "disambiguation_engine",
    "engine",
    "faction_simulation_engine",
    "get_event_bus",
    "main",
    "set_event_bus",
    "to_uuid",
]
