"""The Watcher AI Gameplay Service entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from runefoble_auth.authz_http import install_authz_error_handlers
from runefoble_platform.aggregate_loading import register_store_unavailable_handlers
from runefoble_platform.engine_ports import EngineUnavailableError, engine_unavailable_handler
from runefoble_platform.event_publish import (
    event_publish_failures,
    install_publish_failure_handler,
)
from runefoble_platform.stream_consumer import consumer_statuses
from the_watcher.audience_narration import CONSUMER_NAME, start_audience_narration_consumers
from the_watcher.container import WatcherContainer, build_container
from the_watcher.copilot_state import install_copilot_state_error_handlers
from the_watcher.engine_selection import WatcherEngineSettings
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

ContainerBuilder = Callable[[], WatcherContainer]


def _lifespan_for(build: ContainerBuilder):
    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Build the container first. A missing or bad setting stops start-up (ADR-0015).

        The Redis bus opens before the audience narration consumer starts. A failed
        connection stops start-up.
        """
        container = build()
        app.state.container = container
        bus = await container.event_bus.connect()
        consumers = await start_audience_narration_consumers(bus, container.repositories.whispers)
        app.state.consumers = {CONSUMER_NAME: consumers}
        try:
            await container.copilot.rearm_open_actions()
            yield
        finally:
            await consumers.stop()
            container.copilot.shutdown()
            await container.event_bus.close()
            app.state.consumers = {}

    return _lifespan


def create_app(build: ContainerBuilder = build_container) -> FastAPI:
    """Build the app. The lifespan calls `build` and serves the container it returns."""
    app = FastAPI(
        title="Runefoble - The Watcher Service",
        version="0.1.0",
        description=(
            "AI Gameplay System: Speech-to-Intent, Board Animator, Autonomous DM & "
            "Missing Player Stand-in."
        ),
        lifespan=_lifespan_for(build),
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
    install_copilot_state_error_handlers(app)

    @app.get("/healthz")
    async def health_check(request: Request):
        return {
            "status": "ok",
            "service": "the_watcher",
            "watcher_engine": WatcherEngineSettings().watcher_engine,
            "event_publish_failures": event_publish_failures(),
            "consumers": consumer_statuses(getattr(request.app.state, "consumers", {})),
        }

    return app


# uvicorn serves this app. Nothing is built until its lifespan runs.
app = create_app()


def main():
    import uvicorn

    uvicorn.run("the_watcher.main:app", host="0.0.0.0", port=8001, reload=True)


if __name__ == "__main__":
    main()

__all__ = ["app", "create_app", "main"]
