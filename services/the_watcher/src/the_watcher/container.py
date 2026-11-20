"""Composition root of The Watcher service (ADR-0021 D6, TASK-0916).

`build_container` reads the settings once and builds the engines, the repositories, the
copilot services, and the event bus provider. The app lifespan calls it at start-up and
stores the result on `app.state.container`. No module builds these objects at import time.
"""

from __future__ import annotations

from dataclasses import dataclass

from eventsource.application.aggregates.repository import AggregateRepository
from runefoble_auth.settings import load_spicedb_settings
from runefoble_platform.config import PlatformSettings
from runefoble_platform.event_bus import EventBusProvider
from runefoble_platform.event_sourcing import create_aggregate_repository, get_event_store
from the_watcher.autonomous_dm_engine import AutonomousDMEngine
from the_watcher.chronicle import ChronicleRecapEngine
from the_watcher.compound_actions import CompoundActionEngine
from the_watcher.copilot import CopilotEngine
from the_watcher.copilot_state.disambiguations import DisambiguationAggregate
from the_watcher.copilot_state.pending_actions import PendingActionAggregate
from the_watcher.copilot_state.whispers import WhisperAggregate
from the_watcher.copilot_whispers import WhisperService
from the_watcher.disambiguation import DisambiguationEngine, DisambiguationStore
from the_watcher.engine_selection import load_watcher_ports
from the_watcher.factions import FactionAggregate
from the_watcher.factions.campaign_world import CampaignWorldAggregate
from the_watcher.factions.resources import FactionResourceAggregate
from the_watcher.simulation_engine import FactionSimulationEngine
from the_watcher.turf_war.aggregate import RegionalUnrestAggregate
from the_watcher.watcher_ai import TheWatcherEngine


@dataclass(frozen=True)
class WatcherRepositories:
    """The aggregate repositories of the service."""

    factions: AggregateRepository[FactionAggregate]
    campaign_worlds: AggregateRepository[CampaignWorldAggregate]
    faction_resources: AggregateRepository[FactionResourceAggregate]
    regional_unrest: AggregateRepository[RegionalUnrestAggregate]
    pending_actions: AggregateRepository[PendingActionAggregate]
    whispers: AggregateRepository[WhisperAggregate]
    disambiguations: AggregateRepository[DisambiguationAggregate]


def build_watcher_repositories() -> WatcherRepositories:
    """Build every repository over the process event store provider."""
    return WatcherRepositories(
        factions=create_aggregate_repository(FactionAggregate),
        campaign_worlds=create_aggregate_repository(CampaignWorldAggregate),
        faction_resources=create_aggregate_repository(FactionResourceAggregate),
        regional_unrest=create_aggregate_repository(RegionalUnrestAggregate),
        pending_actions=create_aggregate_repository(PendingActionAggregate),
        whispers=create_aggregate_repository(WhisperAggregate),
        disambiguations=create_aggregate_repository(DisambiguationAggregate),
    )


@dataclass(frozen=True)
class WatcherEngines:
    """The rule engines that the routes call."""

    watcher: TheWatcherEngine
    chronicle: ChronicleRecapEngine
    autonomous_dm: AutonomousDMEngine
    disambiguation: DisambiguationEngine
    compound_actions: CompoundActionEngine
    faction_simulation: FactionSimulationEngine


def build_watcher_engines() -> WatcherEngines:
    return WatcherEngines(
        watcher=TheWatcherEngine(),
        chronicle=ChronicleRecapEngine(),
        autonomous_dm=AutonomousDMEngine(),
        disambiguation=DisambiguationEngine(),
        compound_actions=CompoundActionEngine(),
        faction_simulation=FactionSimulationEngine(),
    )


@dataclass(frozen=True)
class WatcherContainer:
    """Every engine, repository, and copilot service of the app, and the event bus."""

    event_bus: EventBusProvider
    repositories: WatcherRepositories
    engines: WatcherEngines
    copilot: CopilotEngine
    whispers: WhisperService
    disambiguations: DisambiguationStore


def assemble_container(
    event_bus: EventBusProvider,
    repositories: WatcherRepositories,
    engines: WatcherEngines | None = None,
) -> WatcherContainer:
    """Build the copilot services over `repositories`. Check no setting."""
    engines = engines if engines is not None else build_watcher_engines()
    return WatcherContainer(
        event_bus=event_bus,
        repositories=repositories,
        engines=engines,
        copilot=CopilotEngine(pending_repo=repositories.pending_actions),
        whispers=WhisperService(whisper_repo=repositories.whispers, event_bus=event_bus),
        disambiguations=DisambiguationStore(repositories.disambiguations, engines.disambiguation),
    )


def build_container(
    settings: PlatformSettings | None = None, *, event_bus: EventBusProvider | None = None
) -> WatcherContainer:
    """Build the container. Raise at start-up when a required setting is missing.

    - SpiceDB: this service checks permissions, so the preshared key is required (TASK-0720).
    - The event store: build it now. A deployed service without a reachable PostgreSQL
      store, or with the memory store, refuses to start (ADR-0015 (f), TASK-0707).
    - The engine ports: a port setting of `inference_worker` without `RUNEFOBLE_INFERENCE_URL`
      stops start-up.

    `event_bus` replaces the bus provider that the settings select. Tests pass one.
    """
    settings = settings if settings is not None else PlatformSettings()
    load_spicedb_settings()
    get_event_store()
    engines = build_watcher_engines()
    load_watcher_ports(engines.watcher)
    bus = event_bus if event_bus is not None else EventBusProvider(settings)
    return assemble_container(bus, build_watcher_repositories(), engines)


__all__ = [
    "WatcherContainer",
    "WatcherEngines",
    "WatcherRepositories",
    "assemble_container",
    "build_container",
    "build_watcher_engines",
    "build_watcher_repositories",
]
