"""Runefoble Platform Library."""

from runefoble_platform.bus import EventBus, bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup
from runefoble_platform.errors import (
    AuthorizationError,
    EntityNotFoundError,
    GameRuleViolationError,
    RunefobleError,
)
from runefoble_platform.event_sourcing import (
    AggregateRepository,
    DeclarativeAggregate,
    DomainEvent,
    FullEventStore,
    InMemoryEventBus,
    InMemoryEventStore,
    PostgreSQLEventStore,
    RedisEventBus,
    create_aggregate_repository,
    get_event_bus,
    get_event_store,
    handles,
    register_event,
)
from runefoble_platform.models import BaseEntity, CampaignScopedEntity, UserPrincipal, utc_now
from runefoble_platform.redis_bus import RedisStreamsEventBus, deserialize_event

__all__ = [
    "PlatformSettings",
    "BaseEntity",
    "CampaignScopedEntity",
    "UserPrincipal",
    "utc_now",
    "RunefobleError",
    "EntityNotFoundError",
    "AuthorizationError",
    "GameRuleViolationError",
    "EventBus",
    "bus",
    "RedisStreamsEventBus",
    "RedisConsumerGroup",
    "MockAsyncRedis",
    "deserialize_event",
    "DeclarativeAggregate",
    "DomainEvent",
    "AggregateRepository",
    "FullEventStore",
    "InMemoryEventStore",
    "PostgreSQLEventStore",
    "InMemoryEventBus",
    "RedisEventBus",
    "handles",
    "register_event",
    "get_event_store",
    "get_event_bus",
    "create_aggregate_repository",
]
