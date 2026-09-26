"""Event sourcing infrastructure for Runefoble using eventsource-py."""

import logging
import socket
from typing import Any

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
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.platform.event_sourcing")

# Singleton instances for process lifecycle
_global_event_store: FullEventStore | None = None
_global_event_bus: EventBus | None = None


def normalize_async_postgres_url(url: str) -> str:
    """Ensure PostgreSQL DSN uses the asyncpg driver dialect for SQLAlchemy async engine."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


def is_database_reachable(host: str | None, port: int | None, timeout: float = 0.5) -> bool:
    """Probe TCP connectivity to the database host and port."""
    if not host:
        return True
    try:
        with socket.create_connection((host, port or 5432), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


def get_event_store(
    settings: PlatformSettings | None = None,
    *,
    probe_connection: bool = True,
    force_new: bool = False,
) -> FullEventStore:
    """Provide initialized event store: PostgreSQL if configured, or InMemoryEventStore."""
    global _global_event_store
    if _global_event_store is not None and settings is None and not force_new:
        return _global_event_store

    s = settings or PlatformSettings()
    # In local testing or when postgres is not explicitly activated, use InMemoryEventStore
    if getattr(s, "use_postgres_event_store", False):
        try:
            raw_url = str(s.database_url)
            dsn = normalize_async_postgres_url(raw_url)
            parsed = make_url(dsn)

            # Probe TCP reachability if requested and host is present
            if probe_connection and parsed.host:
                port = parsed.port or 5432
                if not is_database_reachable(parsed.host, port):
                    raise ConnectionRefusedError(
                        f"Database host {parsed.host}:{port} is unreachable."
                    )

            logger.info(
                "Initializing PostgreSQLEventStore with DSN: %s",
                parsed.render_as_string(hide_password=True),
            )
            engine_kwargs: dict[str, Any] = {}
            if "postgresql" in parsed.drivername:
                engine_kwargs["pool_size"] = getattr(s, "postgres_pool_size", 5)
                engine_kwargs["max_overflow"] = getattr(s, "postgres_max_overflow", 10)

            engine = create_async_engine(dsn, **engine_kwargs)
            store = PostgreSQLEventStore(
                engine=engine,
                create_schema=True,
                owns_engine=True,
            )
            _global_event_store = store
            return _global_event_store
        except Exception as e:
            logger.warning(
                "Failed to initialize PostgreSQLEventStore (%s). Falling back to InMemory.", e
            )

    _global_event_store = InMemoryEventStore()
    return _global_event_store


def set_event_store(store: FullEventStore | None) -> None:
    """Explicitly set or reset the global event store singleton."""
    global _global_event_store
    _global_event_store = store


def get_event_bus(settings: PlatformSettings | None = None) -> EventBus:
    """Provide event bus: RedisEventBus if configured, or InMemoryEventBus."""
    global _global_event_bus
    if _global_event_bus is not None and settings is None:
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


def set_event_bus(bus: EventBus | None) -> None:
    """Explicitly set or reset the global event bus singleton."""
    global _global_event_bus
    _global_event_bus = bus


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
    "set_event_store",
    "get_event_bus",
    "set_event_bus",
    "create_aggregate_repository",
    "normalize_async_postgres_url",
    "is_database_reachable",
]
