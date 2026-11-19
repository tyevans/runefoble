"""The game session app for in-process tests (ADR-0021 D6 rule 7, TASK-0755).

Tests do not import `game_session.main:app`. They use `session_app`, which `create_app`
builds with a test container. The test container is the production container with one
change: its event bus provider is `session_event_bus`, which the shared harness routes to
the Redis test double (`SERVICE_SEAMS` row `game_session`).

Many tests serve the app without its lifespan (`TestClient(app)` without `with`, or
`serve(app)`). So the helper also stores one container on the app now. A lifespan run
of `session_app` serves the same container.
"""

from __future__ import annotations

from fastapi import FastAPI
from game_session.container import GameSessionContainer, build_container
from game_session.main import create_app
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider

session_event_bus = EventBusProvider(PlatformSettings())
get_event_bus = session_event_bus.get
set_event_bus = session_event_bus.set


def build_test_container() -> GameSessionContainer:
    """Build the production container with the harness event bus."""
    return build_container(event_bus=session_event_bus)


def app_with_container(container: GameSessionContainer) -> FastAPI:
    """Return a new app that serves `container`, with or without its lifespan.

    A test that needs a repository whose store fails replaces it in a copy of the test
    container (`dataclasses.replace`) and serves that copy.
    """
    app = create_app(build=lambda: container)
    app.state.container = container
    return app


session_app = app_with_container(build_test_container())

__all__ = [
    "app_with_container",
    "build_test_container",
    "get_event_bus",
    "session_app",
    "session_event_bus",
    "set_event_bus",
]
