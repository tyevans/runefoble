"""Event sourcing infrastructure for Runefoble using eventsource-py."""

import logging
import socket
from typing import Any, Literal

from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.adapters.postgresql.store import PostgreSQLEventStore
from eventsource.application.aggregates.repository import AggregateRepository
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from eventsource.domain.event import DomainEvent
from eventsource.domain.event_registry import register_event
from eventsource.ports.bus import EventBus
from eventsource.ports.store import FullEventStore
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.platform.event_sourcing")

# Singleton instances for process lifecycle
_global_event_store: FullEventStore | None = None


class EventStoreInitializationError(RuntimeError):
    """Raised when the configured PostgreSQL event store cannot be initialized.

    Services must not run on an in-memory store when persistence is requested.
    """


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


def _require_reachable(parsed: URL) -> None:
    """Raise ConnectionRefusedError when the database host and port do not accept TCP."""
    if not parsed.host:
        return
    port = parsed.port or 5432
    if not is_database_reachable(parsed.host, port):
        raise ConnectionRefusedError(f"Database host {parsed.host}:{port} is unreachable.")


def _build_postgres_store(
    settings: PlatformSettings, *, probe_connection: bool
) -> PostgreSQLEventStore:
    """Build a PostgreSQL event store. Any failure raises EventStoreInitializationError."""
    try:
        dsn = normalize_async_postgres_url(str(settings.database_url))
        parsed = make_url(dsn)
        if probe_connection:
            _require_reachable(parsed)
        logger.info(
            "Initializing PostgreSQLEventStore with DSN: %s",
            parsed.render_as_string(hide_password=True),
        )
        engine_kwargs: dict[str, Any] = {}
        if "postgresql" in parsed.drivername:
            engine_kwargs["pool_size"] = settings.postgres_pool_size
            engine_kwargs["max_overflow"] = settings.postgres_max_overflow
        engine = create_async_engine(dsn, **engine_kwargs)
        return PostgreSQLEventStore(engine=engine, create_schema=True, owns_engine=True)
    except Exception as e:
        raise EventStoreInitializationError(
            f"Failed to initialize PostgreSQLEventStore: {e}"
        ) from e


def get_event_store(
    settings: PlatformSettings | None = None,
    *,
    probe_connection: bool = True,
    force_new: bool = False,
) -> FullEventStore:
    """Provide the process event store for the configured backend.

    The backend defaults to PostgreSQL. The memory backend is accepted only outside
    deployed environments and only when it is selected explicitly. A deployed service
    never runs on InMemoryEventStore. There is no fallback: any initialization failure
    raises EventStoreInitializationError.
    """
    global _global_event_store
    if _global_event_store is not None and settings is None and not force_new:
        return _global_event_store

    s = settings or PlatformSettings()
    if s.event_store_backend == "memory":
        if s.is_deployed:
            raise EventStoreInitializationError(
                f"The memory event store is refused in the '{s.environment}' environment. "
                "Set RUNEFOBLE_EVENT_STORE_BACKEND=postgresql."
            )
        _global_event_store = InMemoryEventStore()
        return _global_event_store

    _global_event_store = _build_postgres_store(s, probe_connection=probe_connection)
    return _global_event_store


def event_store_kind(store: FullEventStore | None = None) -> Literal["postgresql", "memory"]:
    """Report the kind of event store in use: 'postgresql' or 'memory'.

    Uses the process-wide store when no store is given.
    """
    target = store if store is not None else get_event_store()
    if isinstance(target, PostgreSQLEventStore):
        return "postgresql"
    if isinstance(target, InMemoryEventStore):
        return "memory"
    raise TypeError(f"Unsupported event store type: {type(target).__name__}")


def set_event_store(store: FullEventStore | None) -> None:
    """Explicitly set or reset the global event store singleton."""
    global _global_event_store
    _global_event_store = store


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
    "handles",
    "register_event",
    "EventStoreInitializationError",
    "get_event_store",
    "event_store_kind",
    "set_event_store",
    "create_aggregate_repository",
    "normalize_async_postgres_url",
    "is_database_reachable",
]
