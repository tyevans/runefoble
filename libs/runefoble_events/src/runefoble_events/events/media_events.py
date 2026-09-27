"""Voice audio, vocal DSP, soundscape, asset forge, and audience domain events."""

from runefoble_events.asset import (
    AssetDeleted,
    AssetGenerated,
    AssetUploaded,
    BattlemapCreated,
    BattlemapForged,
    TokenAssetForged,
)
from runefoble_events.audience import (
    AudienceModifierApproved,
    AudienceModifierProposed,
    AudiencePollCompleted,
    AudiencePollStarted,
    AudienceVoteCast,
)
from runefoble_events.soundscape import (
    LeitmotifProfileConfigured,
    LeitmotifTriggered,
    SoundscapeCueTriggered,
    SoundscapeDuckingToggled,
    SoundscapeMoodOverridden,
    SoundscapeTensionUpdated,
    SoundscapeTrackChanged,
)
from runefoble_events.vocal_dsp import (
    VocalModulatorPresetApplied,
    VocalModulatorPresetAppliedEvent,
    VoiceFilterToggled,
    VoiceFilterToggledEvent,
)
from runefoble_events.voice import (
    MobileAudioProfileAdapted,
    MobileCompanionConnected,
    MobileHapticPingDispatched,
    VoicePeerJoined,
    VoicePeerLeft,
    VoicePeerMuteToggled,
    VoiceSpeechInterrupted,
)
from runefoble_events.voice_barge_in import (
    NeuralSpeechBargeInDetected,
    NeuralSpeechBargeInDetectedEvent,
    TTSStreamAttenuated,
    TTSStreamAttenuatedEvent,
)
from runefoble_events.voice_stream_quality import (
    VoiceStreamCodecAdaptedEvent,
    VoiceStreamQualityDegradedEvent,
)
from runefoble_events.watcher import (
    VoiceAudioConditioned,
)

__all__ = [
    "AssetDeleted",
    "AssetGenerated",
    "AssetUploaded",
    "AudienceModifierApproved",
    "AudienceModifierProposed",
    "AudiencePollCompleted",
    "AudiencePollStarted",
    "AudienceVoteCast",
    "BattlemapCreated",
    "BattlemapForged",
    "LeitmotifProfileConfigured",
    "LeitmotifTriggered",
    "MobileAudioProfileAdapted",
    "MobileCompanionConnected",
    "MobileHapticPingDispatched",
    "NeuralSpeechBargeInDetected",
    "NeuralSpeechBargeInDetectedEvent",
    "SoundscapeCueTriggered",
    "SoundscapeDuckingToggled",
    "SoundscapeMoodOverridden",
    "SoundscapeTensionUpdated",
    "SoundscapeTrackChanged",
    "TTSStreamAttenuated",
    "TTSStreamAttenuatedEvent",
    "TokenAssetForged",
    "VocalModulatorPresetApplied",
    "VocalModulatorPresetAppliedEvent",
    "VoiceAudioConditioned",
    "VoiceFilterToggled",
    "VoiceFilterToggledEvent",
    "VoicePeerJoined",
    "VoicePeerLeft",
    "VoicePeerMuteToggled",
    "VoiceSpeechInterrupted",
    "VoiceStreamCodecAdaptedEvent",
    "VoiceStreamQualityDegradedEvent",
]
