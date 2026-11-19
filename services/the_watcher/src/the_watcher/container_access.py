"""Read the app container from a request or a WebSocket (ADR-0021 D6 rule 4).

The app lifespan builds the container and stores it on `app.state.container`. Routes read
their part of it through these FastAPI `Depends` providers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from runefoble_platform.event_bus import EventBusProvider
from starlette.requests import HTTPConnection
from the_watcher.container import WatcherContainer, WatcherEngines, WatcherRepositories
from the_watcher.copilot import CopilotEngine
from the_watcher.copilot_whispers import WhisperService
from the_watcher.disambiguation import DisambiguationStore


class ContainerNotBuiltError(RuntimeError):
    """The app has no container. The app lifespan did not run."""


def app_container(conn: HTTPConnection) -> WatcherContainer:
    """Return the container of the app that serves this request or WebSocket."""
    container = getattr(conn.app.state, "container", None)
    if container is None:
        raise ContainerNotBuiltError(
            "The Watcher container is not built. The app lifespan builds it at start-up."
        )
    return container


def _event_bus(conn: HTTPConnection) -> EventBusProvider:
    return app_container(conn).event_bus


def _repositories(conn: HTTPConnection) -> WatcherRepositories:
    return app_container(conn).repositories


def _engines(conn: HTTPConnection) -> WatcherEngines:
    return app_container(conn).engines


def _copilot(conn: HTTPConnection) -> CopilotEngine:
    return app_container(conn).copilot


def _whispers(conn: HTTPConnection) -> WhisperService:
    return app_container(conn).whispers


def _disambiguations(conn: HTTPConnection) -> DisambiguationStore:
    return app_container(conn).disambiguations


EventBus = Annotated[EventBusProvider, Depends(_event_bus)]
Repos = Annotated[WatcherRepositories, Depends(_repositories)]
Engines = Annotated[WatcherEngines, Depends(_engines)]
Copilot = Annotated[CopilotEngine, Depends(_copilot)]
Whispers = Annotated[WhisperService, Depends(_whispers)]
Disambiguations = Annotated[DisambiguationStore, Depends(_disambiguations)]

__all__ = [
    "ContainerNotBuiltError",
    "Copilot",
    "Disambiguations",
    "Engines",
    "EventBus",
    "Repos",
    "Whispers",
    "app_container",
]
