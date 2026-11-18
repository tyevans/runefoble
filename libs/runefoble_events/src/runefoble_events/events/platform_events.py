"""Platform foundation, analytics, compendium, contracts, and tool domain events."""

from runefoble_events.aec import (
    AECBenchmarkCompletedEvent,
    EchoSuppressionEngagedEvent,
)
from runefoble_events.analytics import (
    ChronicleMilestoneRecorded,
    CombatTelemetrySnapshotCreated,
    EncounterMvpAwarded,
)
from runefoble_events.base import BaseRunefobleEvent, register_event
from runefoble_events.compendium import (
    EncounterBalanced,
    HomebrewRuleRegistered,
)
from runefoble_events.contracts import (
    MercenaryBountyClaimed,
    MercenaryBountyFulfilled,
    MercenaryBountyPosted,
)
from runefoble_events.mcp_tools import (
    DynamicToolInvokedEvent,
    DynamicToolRegisteredEvent,
    DynamicToolUnregisteredEvent,
)

__all__ = [
    "AECBenchmarkCompletedEvent",
    "BaseRunefobleEvent",
    "ChronicleMilestoneRecorded",
    "CombatTelemetrySnapshotCreated",
    "DynamicToolInvokedEvent",
    "DynamicToolRegisteredEvent",
    "DynamicToolUnregisteredEvent",
    "EchoSuppressionEngagedEvent",
    "EncounterBalanced",
    "EncounterMvpAwarded",
    "HomebrewRuleRegistered",
    "MercenaryBountyClaimed",
    "MercenaryBountyFulfilled",
    "MercenaryBountyPosted",
    "register_event",
]
