"""NPC faction resource operations and bribery mechanics package."""

from the_watcher.factions.resources.aggregate import FactionResourceAggregate
from the_watcher.factions.resources.bribery import (
    LOYALTY_DC_MODIFIERS,
    ROLE_DC_MODIFIERS,
    calculate_bribery_outcome,
)
from the_watcher.factions.resources.models import (
    BriberyAttemptRequest,
    BriberyAttemptResponse,
    ContrabandItem,
    FactionResourceResponse,
    FactionResourceState,
    MercenaryRecruitRequest,
    MercenaryUnit,
    ResourceAdjustRequest,
)

__all__ = [
    "FactionResourceAggregate",
    "FactionResourceState",
    "MercenaryUnit",
    "ContrabandItem",
    "ResourceAdjustRequest",
    "MercenaryRecruitRequest",
    "BriberyAttemptRequest",
    "BriberyAttemptResponse",
    "FactionResourceResponse",
    "calculate_bribery_outcome",
    "LOYALTY_DC_MODIFIERS",
    "ROLE_DC_MODIFIERS",
]
