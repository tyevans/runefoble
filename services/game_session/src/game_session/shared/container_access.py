"""Read the app container from a request or a WebSocket (ADR-0021 D6 rule 4).

The app lifespan builds the container and stores it on `app.state.container`. Each domain
package reads its own part of the container through a FastAPI `Depends` provider. This
module knows only the attribute name, so it imports no domain package (ADR-0021 D4 rule 5).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Depends
from runefoble_platform.event_bus import EventBusProvider
from starlette.requests import HTTPConnection


class ContainerNotBuiltError(RuntimeError):
    """The app has no container. The app lifespan did not run."""


def app_container(conn: HTTPConnection) -> Any:
    """Return the container of the app that serves this request or WebSocket."""
    container = getattr(conn.app.state, "container", None)
    if container is None:
        raise ContainerNotBuiltError(
            "The game session container is not built. The app lifespan builds it at start-up."
        )
    return container


def event_bus_provider(conn: HTTPConnection) -> EventBusProvider:
    """Return the event bus provider of the container. Call `.get()` to publish."""
    return app_container(conn).event_bus


EventBus = Annotated[EventBusProvider, Depends(event_bus_provider)]

__all__ = ["ContainerNotBuiltError", "EventBus", "app_container", "event_bus_provider"]
