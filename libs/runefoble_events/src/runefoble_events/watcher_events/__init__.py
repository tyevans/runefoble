"""Watcher and gameplay stream domain events package."""

from runefoble_events.watcher_events.actions import (
    CompoundActionResolved,
    IntentDisambiguationRequested,
    VoiceAudioConditioned,
    WatcherActionApproved,
    WatcherActionExpired,
    WatcherActionModified,
    WatcherActionProposed,
    WatcherActionVetoed,
)
from runefoble_events.watcher_events.combat import (
    AutonomousActionResolved,
    CandidateGhostPreviewEmitted,
    DiceRolled,
    DiceRollEvent,
    EncounterSpawned,
)
from runefoble_events.watcher_events.factions import (
    CampaignFactionRegistered,
    FactionAgendaAdvanced,
    FactionAgendaSet,
    FactionCreated,
    GeopoliticalShiftOccurred,
    WorldTickExecuted,
)
from runefoble_events.watcher_events.narrative import (
    AbsenteeRecapGenerated,
    DMNarrativeWhispered,
    PlayerSpokeEvent,
    SceneAtmosphereSet,
    SpeechIntentParsed,
    StandInActionDecided,
    StandInTurnExecuted,
    WatcherNarrationEvent,
    WatcherNarrationGenerated,
)

__all__ = [
    "CampaignFactionRegistered",
    "AbsenteeRecapGenerated",
    "AutonomousActionResolved",
    "CandidateGhostPreviewEmitted",
    "CompoundActionResolved",
    "DMNarrativeWhispered",
    "DiceRollEvent",
    "DiceRolled",
    "EncounterSpawned",
    "FactionAgendaAdvanced",
    "FactionAgendaSet",
    "FactionCreated",
    "GeopoliticalShiftOccurred",
    "IntentDisambiguationRequested",
    "PlayerSpokeEvent",
    "SceneAtmosphereSet",
    "SpeechIntentParsed",
    "StandInActionDecided",
    "StandInTurnExecuted",
    "VoiceAudioConditioned",
    "WatcherActionApproved",
    "WatcherActionExpired",
    "WatcherActionModified",
    "WatcherActionProposed",
    "WatcherActionVetoed",
    "WatcherNarrationEvent",
    "WatcherNarrationGenerated",
    "WorldTickExecuted",
]
