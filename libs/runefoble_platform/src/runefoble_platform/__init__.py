"""Runefoble Platform Library."""

from runefoble_platform.config import PlatformSettings
from runefoble_platform.models import BaseEntity, CampaignScopedEntity, UserPrincipal, utc_now
from runefoble_platform.errors import (
    RunefobleError,
    EntityNotFoundError,
    AuthorizationError,
    GameRuleViolationError,
)
from runefoble_platform.bus import EventBus, bus

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
]
