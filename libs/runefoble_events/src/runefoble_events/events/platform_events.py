"""Platform foundation, analytics, compendium, contracts, and tool domain events."""

from runefoble_events.aec import (
    AECBenchmarkCompleted,
    AECBenchmarkCompletedEvent,
    EchoSuppressionEngaged,
    EchoSuppressionEngagedEvent,
)
from runefoble_events.analytics import (
    ChronicleMilestoneRecorded,
    CombatTelemetrySnapshotCreated,
    EncounterMvpAwarded,
)
from runefoble_events.base import BaseRunefobleEvent, register_event
from runefoble_events.compendium import (
    ConditionIndexed,
    EncounterBalanced,
    HomebrewRuleRegistered,
    MonsterIndexed,
    SpellIndexed,
)
from runefoble_events.contracts import (
    MercenaryBountyClaimed,
    MercenaryBountyClaimedEvent,
    MercenaryBountyFulfilled,
    MercenaryBountyFulfilledEvent,
    MercenaryBountyPosted,
    MercenaryBountyPostedEvent,
)
from runefoble_events.mcp_tools import (
    DynamicToolInvoked,
    DynamicToolInvokedEvent,
    DynamicToolRegistered,
    DynamicToolRegisteredEvent,
    DynamicToolUnregistered,
    DynamicToolUnregisteredEvent,
)

__all__ = [
    "AECBenchmarkCompleted",
    "AECBenchmarkCompletedEvent",
    "BaseRunefobleEvent",
    "ChronicleMilestoneRecorded",
    "CombatTelemetrySnapshotCreated",
    "ConditionIndexed",
    "DynamicToolInvoked",
    "DynamicToolInvokedEvent",
    "DynamicToolRegistered",
    "DynamicToolRegisteredEvent",
    "DynamicToolUnregistered",
    "DynamicToolUnregisteredEvent",
    "EchoSuppressionEngaged",
    "EchoSuppressionEngagedEvent",
    "EncounterBalanced",
    "EncounterMvpAwarded",
    "HomebrewRuleRegistered",
    "MercenaryBountyClaimed",
    "MercenaryBountyClaimedEvent",
    "MercenaryBountyFulfilled",
    "MercenaryBountyFulfilledEvent",
    "MercenaryBountyPosted",
    "MercenaryBountyPostedEvent",
    "MonsterIndexed",
    "SpellIndexed",
    "register_event",
]
