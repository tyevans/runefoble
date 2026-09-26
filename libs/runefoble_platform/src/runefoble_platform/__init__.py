"""Runefoble Platform Library."""

from runefoble_platform.analytics import (
    AnalyticsEventWorker,
    OpenPanelClient,
    anonymize_profile_id,
    sanitize_properties,
)
from runefoble_platform.bus import EventBus, bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.consumer_group import MockAsyncRedis, RedisConsumerGroup
from runefoble_platform.dice import DICE_FORMULA_PATTERN, evaluate_dice, parse_and_roll
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
from runefoble_platform.storage import (
    ALLOWED_MIME_TYPES,
    MAX_ASSET_SIZE_BYTES,
    AssetNotFoundError,
    AssetStorageError,
    AssetValidationError,
    SiloStorageService,
    get_storage_service,
    set_storage_service,
)
from runefoble_platform.telemetry import (
    extract_trace_context,
    get_tracer,
    init_telemetry,
    inject_trace_context,
    instrument_fastapi,
    reset_tracer_provider,
    trace_span,
    uninstrument_fastapi,
)

__all__ = [
    "evaluate_dice",
    "parse_and_roll",
    "DICE_FORMULA_PATTERN",
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
    "OpenPanelClient",
    "AnalyticsEventWorker",
    "anonymize_profile_id",
    "sanitize_properties",
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
    "SiloStorageService",
    "get_storage_service",
    "set_storage_service",
    "AssetStorageError",
    "AssetValidationError",
    "AssetNotFoundError",
    "ALLOWED_MIME_TYPES",
    "MAX_ASSET_SIZE_BYTES",
    "init_telemetry",
    "instrument_fastapi",
    "uninstrument_fastapi",
    "reset_tracer_provider",
    "get_tracer",
    "inject_trace_context",
    "extract_trace_context",
    "trace_span",
]
