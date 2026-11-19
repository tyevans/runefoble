"""The Watcher app for in-process tests (ADR-0021 D6 rule 7, TASK-0916).

Tests do not import `the_watcher.main:app`. They use `watcher_app`, which `create_app` builds
with a test container. The test container is the production container with one change: its
event bus provider is `watcher_event_bus`, which the shared harness routes to the Redis test
double (`SERVICE_SEAMS` row `the_watcher`).

Many tests serve the app without its lifespan (`TestClient(app)` without `with`, or an ASGI
transport). So the helper also stores one container on the app now. A lifespan run of
`watcher_app` serves the same container.
"""

from __future__ import annotations

from eventsource.adapters.memory.store import InMemoryEventStore
from fastapi import FastAPI
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import create_aggregate_repository
from the_watcher.container import (
    WatcherContainer,
    WatcherRepositories,
    assemble_container,
    build_container,
)
from the_watcher.copilot_state.disambiguations import DisambiguationAggregate
from the_watcher.copilot_state.pending_actions import PendingActionAggregate
from the_watcher.copilot_state.whispers import WhisperAggregate
from the_watcher.factions import FactionAggregate
from the_watcher.factions.campaign_world import CampaignWorldAggregate
from the_watcher.factions.resources import FactionResourceAggregate
from the_watcher.main import create_app
from the_watcher.turf_war.aggregate import RegionalUnrestAggregate

watcher_event_bus = EventBusProvider(PlatformSettings())
get_event_bus = watcher_event_bus.get
set_event_bus = watcher_event_bus.set


def build_test_container() -> WatcherContainer:
    """Build the production container with the harness event bus."""
    return build_container(event_bus=watcher_event_bus)


def repositories_over(store: InMemoryEventStore) -> WatcherRepositories:
    """Build every repository over one given event store."""
    return WatcherRepositories(
        factions=create_aggregate_repository(FactionAggregate, event_store=store),
        campaign_worlds=create_aggregate_repository(CampaignWorldAggregate, event_store=store),
        faction_resources=create_aggregate_repository(FactionResourceAggregate, event_store=store),
        regional_unrest=create_aggregate_repository(RegionalUnrestAggregate, event_store=store),
        pending_actions=create_aggregate_repository(PendingActionAggregate, event_store=store),
        whispers=create_aggregate_repository(WhisperAggregate, event_store=store),
        disambiguations=create_aggregate_repository(DisambiguationAggregate, event_store=store),
    )


def container_over(repositories: WatcherRepositories) -> WatcherContainer:
    """Build a test container whose repositories and copilot services use `repositories`.

    A restart test calls it twice with the same repositories. The second container has a
    new copilot engine over the same stores.
    """
    return assemble_container(watcher_event_bus, repositories)


def fresh_store_container() -> WatcherContainer:
    """Build a test container over one new, empty event store."""
    return container_over(repositories_over(InMemoryEventStore()))


def app_with_container(container: WatcherContainer) -> FastAPI:
    """Return a new app that serves `container`, with or without its lifespan."""
    app = create_app(build=lambda: container)
    app.state.container = container
    return app


def app_built_at_start_up() -> FastAPI:
    """Return a new app whose lifespan builds the test container, so start-up checks run."""
    return create_app(build=build_test_container)


watcher_app = app_with_container(build_test_container())

__all__ = [
    "app_built_at_start_up",
    "app_with_container",
    "build_test_container",
    "container_over",
    "fresh_store_container",
    "get_event_bus",
    "repositories_over",
    "set_event_bus",
    "watcher_app",
    "watcher_event_bus",
]
