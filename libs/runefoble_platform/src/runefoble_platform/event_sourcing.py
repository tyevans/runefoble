"""Event sourcing infrastructure for Runefoble using eventsource-py."""

import logging
import socket
from collections.abc import AsyncIterator, Sequence
from typing import Any, Literal

from eventsource.adapters.memory.store import InMemoryEventStore
from eventsource.adapters.postgresql.store import PostgreSQLEventStore
from eventsource.application.aggregates.repository import AggregateRepository
from eventsource.domain import StreamId
from eventsource.domain.aggregate import DeclarativeAggregate
from eventsource.domain.decorators import handles
from eventsource.domain.event import DomainEvent
from eventsource.domain.event_registry import register_event
from eventsource.ports.bus import EventBus
from eventsource.ports.envelopes import AppendResult, EventEnvelope, StreamReadOptions
from eventsource.ports.positions import ExpectedVersion
from eventsource.ports.store import AggregateStore, FullEventStore
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import create_async_engine

from runefoble_platform.config import PlatformSettings

logger = logging.getLogger("runefoble.platform.event_sourcing")


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


def build_event_store(
    settings: PlatformSettings, *, probe_connection: bool = True
) -> FullEventStore:
    """Build a new event store for the configured backend. It is not cached.

    The backend defaults to PostgreSQL. The memory backend is accepted only outside
    deployed environments and only when it is selected explicitly. A deployed service
    never runs on InMemoryEventStore. There is no fallback: any initialization failure
    raises EventStoreInitializationError.
    """
    if settings.event_store_backend == "memory":
        if settings.is_deployed:
            raise EventStoreInitializationError(
                f"The memory event store is refused in the '{settings.environment}' environment. "
                "Set RUNEFOBLE_EVENT_STORE_BACKEND=postgresql."
            )
        return InMemoryEventStore()
    return _build_postgres_store(settings, probe_connection=probe_connection)


class EventStoreProvider:
    """Own the process event store. It is built lazily from settings and replaced by `set`.

    Repositories never hold a store. They resolve it here on every operation (see
    `ProvidedEventStore`), so a replaced store reaches every route at once (TASK-0773).
    """

    def __init__(self, settings: PlatformSettings | None = None) -> None:
        self._settings = settings
        self._store: FullEventStore | None = None

    def get(self) -> FullEventStore:
        """Return the store. Build it on first use from settings (default: the environment)."""
        if self._store is None:
            settings = self._settings if self._settings is not None else PlatformSettings()
            self._store = build_event_store(settings)
        return self._store

    def set(self, store: FullEventStore | None) -> None:
        """Replace the store. None resets it, so the next `get` builds one again."""
        self._store = store


event_store_provider = EventStoreProvider()


def get_event_store() -> FullEventStore:
    """Return the process event store through the provider."""
    return event_store_provider.get()


def set_event_store(store: FullEventStore | None) -> None:
    """Replace the process event store through the provider. None resets it."""
    event_store_provider.set(store)


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


class ProvidedEventStore:
    """An aggregate store that forwards each call to the provider's current store."""

    def __init__(self, provider: EventStoreProvider) -> None:
        self._provider = provider

    async def append(
        self,
        stream: StreamId,
        events: Sequence[DomainEvent],
        expected: ExpectedVersion,
    ) -> AppendResult:
        return await self._provider.get().append(stream, events, expected)

    def read_stream(
        self,
        stream: StreamId,
        options: StreamReadOptions | None = None,
    ) -> AsyncIterator[EventEnvelope]:
        return self._provider.get().read_stream(stream, options)

    async def get_stream_version(self, stream: StreamId) -> int:
        return await self._provider.get().get_stream_version(stream)


def create_aggregate_repository[T: DeclarativeAggregate](
    aggregate_factory: type[T],
    event_store: AggregateStore | None = None,
    event_bus: EventBus | None = None,
) -> AggregateRepository[T]:
    """Create an AggregateRepository. Without `event_store`, it resolves the provider's store."""
    store: AggregateStore = (
        event_store if event_store is not None else ProvidedEventStore(event_store_provider)
    )
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
    "build_event_store",
    "event_store_provider",
    "EventStoreProvider",
    "ProvidedEventStore",
    "get_event_store",
    "event_store_kind",
    "set_event_store",
    "create_aggregate_repository",
    "normalize_async_postgres_url",
    "is_database_reachable",
]
