"""Event sourcing infrastructure for Runefoble using eventsource-py."""

import logging

from eventsource.adapters.memory.bus import InMemoryEventBus
from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.adapters.postgresql.store import PostgreSQLEventStore
from eventsource.adapters.redis.bus import RedisEventBus, RedisEventBusConfig
from eventsource.application.aggregates.repository import AggregateRepository
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from eventsource.domain.event import DomainEvent
from eventsource.domain.event_registry import register_event
from eventsource.ports.bus import EventBus
from eventsource.ports.store import FullEventStore

from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.platform.event_sourcing")

# Singleton instances for process lifecycle
_global_event_store: FullEventStore | None = None
_global_event_bus: EventBus | None = None


def get_event_store(settings: PlatformSettings | None = None) -> FullEventStore:
    """Provide initialized event store: PostgreSQL if configured, or InMemoryEventStore."""
    global _global_event_store
    if _global_event_store is not None:
        return _global_event_store

    s = settings or PlatformSettings()
    # In local testing or when postgres is not explicitly activated, use InMemoryEventStore
    if getattr(s, "use_postgres_event_store", False):
        try:
            logger.info("Initializing PostgreSQLEventStore...")
            _global_event_store = PostgreSQLEventStore(
                dsn=str(s.postgres_dsn),
                table_name="runefoble_events",
            )
            return _global_event_store
        except Exception as e:
            logger.warning(
                "Failed to initialize PostgreSQLEventStore (%s). Falling back to InMemory.", e
            )

    _global_event_store = InMemoryEventStore()
    return _global_event_store


def get_event_bus(settings: PlatformSettings | None = None) -> EventBus:
    """Provide event bus: RedisEventBus if configured, or InMemoryEventBus."""
    global _global_event_bus
    if _global_event_bus is not None:
        return _global_event_bus

    s = settings or PlatformSettings()
    if getattr(s, "use_redis_event_bus", False):
        try:
            logger.info("Initializing RedisEventBus...")
            config = RedisEventBusConfig(redis_url=str(s.redis_url))
            _global_event_bus = RedisEventBus(config=config)
            return _global_event_bus
        except Exception as e:
            logger.warning("Failed to initialize RedisEventBus (%s). Falling back to InMemory.", e)

    _global_event_bus = InMemoryEventBus()
    return _global_event_bus


def create_aggregate_repository[T: DeclarativeAggregate](
    aggregate_factory: type[T],
    event_store: FullEventStore | None = None,
    event_bus: EventBus | None = None,
) -> AggregateRepository[T]:
    """Create an AggregateRepository configured with default or provided event store and bus."""
    store = event_store or get_event_store()
    return AggregateRepository(
        event_store=store,
        aggregate_factory=aggregate_factory,
        event_publisher=event_bus,
    )


__all__ = [
    "DeclarativeAggregate",
    "DomainEvent",
    "AggregateRepository",
    "FullEventStore",
    "InMemoryEventStore",
    "PostgreSQLEventStore",
    "EventBus",
    "InMemoryEventBus",
    "RedisEventBus",
    "handles",
    "register_event",
    "get_event_store",
    "get_event_bus",
    "create_aggregate_repository",
]
