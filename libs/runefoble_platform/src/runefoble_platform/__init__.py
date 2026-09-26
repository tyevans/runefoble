"""Runefoble Platform Library."""

from runefoble_platform.bus import EventBus, bus
from runefoble_platform.config import PlatformSettings
from runefoble_platform.errors import (
    AuthorizationError,
    EntityNotFoundError,
    GameRuleViolationError,
    RunefobleError,
)
from runefoble_platform.models import BaseEntity, CampaignScopedEntity, UserPrincipal, utc_now
from runefoble_platform.redis_bus import RedisStreamsEventBus

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
]
