"""The Watcher AI Gameplay Service entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.engine_ports import EngineUnavailableError, engine_unavailable_handler
from runefoble_platform.event_publish import (
    event_publish_failures,
    install_publish_failure_handler,
)
from the_watcher.authz_errors import install_authz_error_handlers
from the_watcher.dependencies import (
    STREAM_BOARD,
    STREAM_WATCHER,
    autonomous_dm_engine,
    chronicle_engine,
    compound_action_engine,
    disambiguation_engine,
    engine,
    event_bus_provider,
    get_event_bus,
    set_event_bus,
    to_uuid,
)
from the_watcher.engine_selection import WatcherEngineSettings, load_watcher_ports
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
    turf_war_router,
    ui_manifest_router,
)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Select the engine ports first. A missing worker URL or a bad setting stops start-up."""
    load_watcher_ports(engine)
    async with event_bus_provider.lifespan(app):
        yield


app = FastAPI(
    title="Runefoble - The Watcher Service",
    version="0.1.0",
    description="AI Gameplay System: Speech-to-Intent, Board Animator, Autonomous DM & Missing Player Stand-in.",
    lifespan=_lifespan,
)

register_store_unavailable_handlers(app)
app.add_exception_handler(EngineUnavailableError, engine_unavailable_handler)
app.include_router(intent_router)
app.include_router(autonomous_dm_router)
app.include_router(stand_in_router)
app.include_router(chronicle_router)
app.include_router(copilot_router)
app.include_router(factions_router)
app.include_router(faction_resources_router)
app.include_router(turf_war_router)
app.include_router(ui_manifest_router)
install_publish_failure_handler(app)
install_authz_error_handlers(app)


@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service": "the_watcher",
        "watcher_engine": WatcherEngineSettings().watcher_engine,
        "event_publish_failures": event_publish_failures(),
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
    "get_event_bus",
    "main",
    "set_event_bus",
    "to_uuid",
]
